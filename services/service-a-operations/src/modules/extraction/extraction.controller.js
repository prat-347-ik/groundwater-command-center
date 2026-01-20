import axios from 'axios';
import ExtractionLog from '../../models/ExtractionLog.model.js';
import Region from '../../models/Region.model.js';

// Configuration (In production, use process.env.SERVICE_B_URL)
const SERVICE_B_URL = 'http://localhost:8000/api/v1/forecasts';

export const createLog = async (req, res, next) => {
  try {
    const { region_id, volume_liters, usage_type } = req.body;

    // 1. Basic Validation
    if (!region_id || !volume_liters) {
      const error = new Error('Missing region_id or volume_liters');
      error.status = 400;
      throw error;
    }

    // 2. Fetch Region Settings
    const region = await Region.findOne({ region_id });
    if (!region) {
      const error = new Error('Region not found');
      error.status = 404;
      throw error;
    }

   // --- 🛡️ SAFE YIELD ENFORCEMENT START ---
    
    // A. Ask Service B for the Forecast
    let predictedLevel = null;
    try {
      const response = await axios.get(`${SERVICE_B_URL}/${region_id}`);
      const forecasts = response.data;
      
      if (forecasts && forecasts.length > 0) {
        predictedLevel = Math.min(...forecasts.map(f => f.predicted_level));
      }
    } catch (err) {
      console.warn("⚠️ Service B Unreachable. Proceeding with caution (Fail Open).");
    }

    // B. Calculate Impact using REAL PHYSICS
    if (predictedLevel !== null) {
      const volume_m3 = volume_liters / 1000.0;
      const area = region.aquifer_area_m2 || 1000000; 
      const sy = region.specific_yield || 0.15;

      const estimatedDrop = volume_m3 / (area * sy);
      const finalLevel = predictedLevel - estimatedDrop;

      console.log(`🔍 Physics Check: Vol=${volume_m3}m³ | Area=${area}m² | Sy=${sy}`);
      console.log(`   📉 Predicted Drop: ${estimatedDrop.toFixed(4)}m | Final Level: ${finalLevel.toFixed(4)}m`);

      // C. The Decision (Block if Unsafe)
      if (finalLevel < region.critical_water_level_m) {
        return res.status(409).json({
          success: false,
          error: "Unsafe Yield: Extraction denied.",
          details: {
            reason: "Groundwater levels critically low.",
            predicted_level_next_7d: predictedLevel,
            impact_of_extraction: -estimatedDrop,
            critical_limit: region.critical_water_level_m,
            physics_used: { area_m2: area, specific_yield: sy },
            message: "Please reduce extraction volume or wait for recharge."
          }
        });
      }
    }
    // --- 🛡️ SAFE YIELD ENFORCEMENT END ---

    // ✅ FIXED: 3. Create Log & Send Success Response (This was missing)
    const log = await ExtractionLog.create({
      region_id,
      volume_liters,
      usage_type
    });

    res.status(201).json({ success: true, data: log });

  } catch (error) {
    next(error);
  }
};
// @desc    Get extraction history for a region
// @route   GET /api/v1/extraction/:region_id
export const getExtractionHistory = async (req, res, next) => {
  try {
    const { region_id } = req.params;
    const { start_date, end_date } = req.query;

    const query = { region_id };

    // Date Filtering
    if (start_date || end_date) {
      query.timestamp = {};
      if (start_date) query.timestamp.$gte = new Date(start_date);
      if (end_date) query.timestamp.$lte = new Date(end_date);
    }

    const logs = await ExtractionLog.find(query).sort({ timestamp: -1 });

    res.status(200).json({
      success: true,
      count: logs.length,
      data: logs
    });
  } catch (error) {
    next(error);
  }
};