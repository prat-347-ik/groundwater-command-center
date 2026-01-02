import fs from 'fs';
import csv from 'csv-parser';
import WaterReading from '../../models/WaterReading.model.js';
import Well from '../../models/Well.model.js';
import Region from '../../models/Region.model.js';

// ==========================================
// 1️⃣ Manual API (Single Insert)
// ==========================================
// @desc    Ingest a single water reading
// @route   POST /api/v1/water-readings
export const createReading = async (req, res, next) => {
  try {
    const { well_id, region_id, water_level, source, timestamp } = req.body;

    // 1. Validation
    if (!well_id || !region_id || water_level === undefined || !source) {
      const error = new Error('Missing required fields: well_id, region_id, water_level, source');
      error.status = 400;
      throw error;
    }

    if (typeof water_level !== 'number') {
      const error = new Error('water_level must be a number');
      error.status = 400;
      throw error;
    }

    // 2. Integrity Check: Does the Region exist & is it active?
    const region = await Region.findOne({ region_id });
    if (!region) {
      const error = new Error(`Region ${region_id} not found`);
      error.status = 404;
      throw error;
    }
    if (region.is_active === false) {
      const error = new Error(`Region ${region.name} is inactive. Cannot ingest data.`);
      error.status = 409;
      throw error;
    }

    // 3. Integrity Check: Does the Well exist in this Region?
    const well = await Well.findOne({ well_id, region_id });
    if (!well) {
      const error = new Error(`Well ${well_id} does not exist in Region ${region_id}`);
      error.status = 404;
      throw error;
    }

    // 4. Save
    const reading = await WaterReading.create({
      well_id,
      region_id,
      water_level,
      source,
      timestamp: timestamp || new Date()
    });

    res.status(201).json({ success: true, data: reading });

  } catch (error) {
    next(error);
  }
};

// ==========================================
// 2️⃣ CSV Batch Ingestion (Stream + Batch)
// ==========================================
// @desc    Ingest bulk readings via CSV
// @route   POST /api/v1/water-readings/ingest/csv
export const ingestReadingsCSV = async (req, res, next) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No CSV file uploaded' });
  }

  const results = {
    totalRows: 0,
    inserted: 0,
    failed: 0,
    errors: []
  };

  const BATCH_SIZE = 500; // Process 500 rows at a time
  let batch = [];

  // Helper: Process a batch of rows
  const processBatch = async (rows) => {
    const validReadings = [];
    const wellIds = rows.map(r => r.well_id);
    const regionIds = rows.map(r => r.region_id);

    // Bulk Lookup: Get all valid active wells for these IDs
    // We assume if the well exists, the region link is valid (simplified for speed)
    // or strictly check { well_id, region_id } pairs if needed.
    const foundWells = await Well.find({ 
      well_id: { $in: wellIds },
      region_id: { $in: regionIds } // basic check
    }).select('well_id region_id').lean();

    // Create a Set for O(1) lookup: "wellId|regionId"
    const validWellMap = new Set(foundWells.map(w => `${w.well_id}|${w.region_id}`));

    for (const row of rows) {
      const { well_id, region_id, water_level, timestamp, source } = row;
      const key = `${well_id}|${region_id}`;

      // Validation 1: Logic
      if (!validWellMap.has(key)) {
        results.failed++;
        results.errors.push({ row: row, reason: 'Well/Region mismatch or not found' });
        continue;
      }

      // Validation 2: Data Types
      const level = parseFloat(water_level);
      if (isNaN(level)) {
        results.failed++;
        results.errors.push({ row: row, reason: 'Invalid water_level' });
        continue;
      }

      validReadings.push({
        well_id,
        region_id,
        water_level: level,
        source: source || 'csv_upload',
        timestamp: timestamp ? new Date(timestamp) : new Date()
      });
    }

    if (validReadings.length > 0) {
      await WaterReading.insertMany(validReadings);
      results.inserted += validReadings.length;
    }
  };

  // Start Streaming
  const stream = fs.createReadStream(req.file.path)
    .pipe(csv())
    .on('data', (data) => {
      results.totalRows++;
      
      // Basic Structure Validation
      if (!data.well_id || !data.region_id || !data.water_level) {
        results.failed++;
        // limit error log size
        if (results.errors.length < 50) {
            results.errors.push({ row: data, reason: 'Missing required columns' });
        }
        return;
      }

      batch.push(data);

      if (batch.length >= BATCH_SIZE) {
        stream.pause(); // ⏸️ Pause stream while DB writes
        processBatch(batch).then(() => {
          batch = []; // Clear batch
          stream.resume(); // ▶️ Resume stream
        }).catch(err => {
          console.error('Batch Insert Error:', err);
          stream.destroy(); // Stop on critical DB error
          res.status(500).json({ error: 'Database batch write failed' });
        });
      }
    })
    .on('end', async () => {
      // Process remaining rows
      if (batch.length > 0) {
        await processBatch(batch);
      }
      
      // Clean up file
      fs.unlinkSync(req.file.path);

      res.status(200).json({
        success: true,
        summary: {
          total_processed: results.totalRows,
          inserted: results.inserted,
          failed: results.failed
        },
        sample_errors: results.errors.slice(0, 20) // Only show first 20 errors
      });
    })
    .on('error', (err) => {
      res.status(500).json({ error: 'Failed to parse CSV', details: err.message });
    });
};

// @desc    Get readings for a specific well (Verification)
// @route   GET /api/v1/water-readings/wells/:wellId
export const getReadingsByWell = async (req, res, next) => {
  try {
    const { wellId } = req.params;
    const readings = await WaterReading.find({ well_id: wellId })
      .sort({ timestamp: -1 })
      .limit(100);

    res.status(200).json({ success: true, count: readings.length, data: readings });
  } catch (error) {
    next(error);
  }
};

// @desc    Get readings with filters (Region, Date Range)
// @route   GET /api/v1/water-readings
export const getReadings = async (req, res, next) => {
  try {
    const { region_id, well_id, from, to, limit, sort } = req.query;

    const query = {};

    // 1. Apply Filters
    if (region_id) query.region_id = region_id;
    if (well_id) query.well_id = well_id;

    // 2. Date Range Filter (Critical for Dashboards)
    // "Give me data for the last 30 days"
    if (from || to) {
      query.timestamp = {};
      if (from) query.timestamp.$gte = new Date(from);
      if (to) query.timestamp.$lte = new Date(to);
    }

    // 3. Safety Limits (Protect the UI from 1M rows)
    const MAX_LIMIT = 2000;
    const effectiveLimit = limit ? Math.min(parseInt(limit), MAX_LIMIT) : 500;

    // 4. Sorting
    // Default: Ascending (1) = Oldest to Newest (Best for Graphs 📈)
    // Option: Descending (-1) = Newest first (Best for Activity Logs 📋)
    const sortOrder = sort === 'desc' ? -1 : 1;

    const readings = await WaterReading.find(query)
      .sort({ timestamp: sortOrder })
      .limit(effectiveLimit)
      .lean(); // Faster for read-only data

    res.status(200).json({
      success: true,
      count: readings.length,
      filters: {
        region_id,
        from,
        to
      },
      data: readings
    });

  } catch (error) {
    next(error);
  }
};