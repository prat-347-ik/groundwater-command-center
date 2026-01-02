import fs from 'fs';
import csv from 'csv-parser';
import Rainfall from '../../models/Rainfall.model.js';
import Region from '../../models/Region.model.js';

// ==========================================
// 1️⃣ Manual API (Single Insert)
// ==========================================
// @desc    Ingest a single rainfall record
// @route   POST /api/v1/rainfall
export const createRainfall = async (req, res, next) => {
  try {
    const { region_id, amount_mm, source, timestamp } = req.body;

    // 1. Validation
    if (!region_id || amount_mm === undefined) {
      const error = new Error('Missing required fields: region_id, amount_mm');
      error.status = 400;
      throw error;
    }

    if (typeof amount_mm !== 'number' || amount_mm < 0) {
      const error = new Error('amount_mm must be a non-negative number');
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
      const error = new Error(`Region ${region.name} is inactive. Cannot ingest rainfall data.`);
      error.status = 409;
      throw error;
    }

    // 3. Save
    const rainfall = await Rainfall.create({
      region_id,
      amount_mm,
      source: source || 'manual',
      timestamp: timestamp || new Date()
    });

    res.status(201).json({
      message: "Rainfall record created",
      data: rainfall 
    });

  } catch (error) {
    next(error);
  }
};

// ==========================================
// 2️⃣ CSV Batch Ingestion (Stream + Batch)
// ==========================================
export const ingestRainfallCSV = async (req, res, next) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No CSV file uploaded' });
  }

  const results = {
    totalRows: 0,
    inserted: 0,
    failed: 0,
    errors: []
  };

  const BATCH_SIZE = 500;
  let batch = [];
  let isFileFormatInvalid = false; // Flag to stop processing if format is wrong

  // Helper: Process a batch of rows
  const processBatch = async (rows) => {
    if (rows.length === 0) return;

    const validRecords = [];
    const regionIds = rows.map(r => r.region_id);

    // Bulk Lookup: Validate Regions
    const foundRegions = await Region.find({ 
      region_id: { $in: regionIds },
      is_active: true
    }).select('region_id').lean();

    const validRegionSet = new Set(foundRegions.map(r => r.region_id));

    for (const row of rows) {
      const { region_id, amount_mm, timestamp, source } = row;

      // Validation 1: Logic
      if (!validRegionSet.has(region_id)) {
        results.failed++;
        results.errors.push({ row: row, reason: 'Region not found or inactive' });
        continue;
      }

      // Validation 2: Data Types
      const amount = parseFloat(amount_mm);
      if (isNaN(amount) || amount < 0) {
        results.failed++;
        results.errors.push({ row: row, reason: 'Invalid amount_mm' });
        continue;
      }

      validRecords.push({
        region_id,
        amount_mm: amount,
        source: source || 'csv_upload',
        timestamp: timestamp ? new Date(timestamp) : new Date()
      });
    }

    if (validRecords.length > 0) {
      await Rainfall.insertMany(validRecords);
      results.inserted += validRecords.length;
    }
  };

  // Start Streaming
  const stream = fs.createReadStream(req.file.path)
    .pipe(csv({
      separator: ',',                         // 🔒 FORCE comma separator
      mapHeaders: ({ header }) => header.trim() // ✂️ TRIM whitespace from headers
    }))
    .on('data', (data) => {
      // 🚨 CRITICAL CHECK: Did the parser fail to split columns?
      // If we see a key that looks like "region_id,amount_mm...", the parser failed.
      const keys = Object.keys(data);
      if (keys.length === 1 && keys[0].includes(',')) {
        isFileFormatInvalid = true;
        stream.destroy(); // Stop reading immediately
        return;
      }

      results.totalRows++;
      
      // Basic Structure Validation
      if (!data.region_id || !data.amount_mm) {
        results.failed++;
        if (results.errors.length < 50) {
            results.errors.push({ row: data, reason: 'Missing required columns (Check CSV headers)' });
        }
        return;
      }

      batch.push(data);

      if (batch.length >= BATCH_SIZE) {
        stream.pause();
        processBatch(batch).then(() => {
          batch = [];
          stream.resume();
        }).catch(err => {
          console.error('Batch Insert Error:', err);
          stream.destroy();
          // We can't send a response here easily if headers are sent, 
          // but we rely on the 'close' or 'error' handlers usually.
        });
      }
    })
    .on('close', async () => {
      // 🚨 Handle the specific invalid format error
      if (isFileFormatInvalid) {
        fs.unlinkSync(req.file.path);
        return res.status(400).json({
          error: "CSV Format Error",
          message: "The server could not parse the columns. Please ensure your CSV uses valid Comma Separators (,) and is UTF-8 encoded."
        });
      }

      // Process remaining rows
      if (batch.length > 0) {
        await processBatch(batch);
      }
      
      // Cleanup
      if (fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);

      res.status(200).json({
        message: "Rainfall CSV processed",
        total_rows: results.totalRows,
        inserted: results.inserted,
        failed: results.failed,
        sample_errors: results.errors.slice(0, 20)
      });
    })
    .on('error', (err) => {
      if (fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
      res.status(500).json({ error: 'Failed to parse CSV', details: err.message });
    });
};


// ==========================================
// 3️⃣ Read Rainfall (Filtering & Dashboards)
// ==========================================
// @desc    Get rainfall data with filters
// @route   GET /api/v1/rainfall
export const getRainfall = async (req, res, next) => {
  try {
    const { region_id, from, to, limit, sort } = req.query;

    const query = {};

    // 1. Apply Filters
    if (region_id) query.region_id = region_id;

    // 2. Date Range Filter
    if (from || to) {
      query.timestamp = {};
      if (from) query.timestamp.$gte = new Date(from);
      if (to) query.timestamp.$lte = new Date(to);
    }

    // 3. Safety Limits
    const MAX_LIMIT = 2000;
    const effectiveLimit = limit ? Math.min(parseInt(limit), MAX_LIMIT) : 500;

    // 4. Sorting
    const sortOrder = sort === 'desc' ? -1 : 1;

    const rainfallData = await Rainfall.find(query)
      .sort({ timestamp: sortOrder })
      .limit(effectiveLimit)
      .lean();

    res.status(200).json({
      count: rainfallData.length,
      filters: { region_id, from, to },
      data: rainfallData
    });

  } catch (error) {
    next(error);
  }
};

// ==========================================
// 4️⃣ Health / Debug Stats
// ==========================================
// @desc    Get basic rainfall stats (Admin/Debug)
// @route   GET /api/v1/rainfall/stats
export const getRainfallStats = async (req, res, next) => {
  try {
    // Basic aggregation to verify data flow
    const stats = await Rainfall.aggregate([
      {
        $group: {
          _id: "$region_id",
          total_records: { $sum: 1 },
          last_recorded: { $max: "$timestamp" },
          total_rain_recorded: { $sum: "$amount_mm" } // Rough sum, be careful with large datasets
        }
      }
    ]);

    res.status(200).json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
};