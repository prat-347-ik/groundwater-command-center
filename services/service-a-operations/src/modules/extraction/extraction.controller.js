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
    // We want to know: "If nothing happens, where will the water be?"
    let predictedLevel = null;
    try {
      // Get the 7-day forecast
      const response = await axios.get(`${SERVICE_B_URL}/${region_id}`);
      const forecasts = response.data;
      
      if (forecasts && forecasts.length > 0) {
        // Look at the lowest point in the next 7 days (Worst Case Scenario)
        // We use Math.min(...) to be conservative
        predictedLevel = Math.min(...forecasts.map(f => f.predicted_level));
      }
    } catch (err) {
      console.warn("⚠️ Service B Unreachable. Proceeding with caution (Fail Open).");
      // In strict mode, you might throw an error here to 'Fail Closed'
    }

    // B. Calculate Impact
    if (predictedLevel !== null) {
      // Rough Physics: 100,000L extracted ≈ 0.1m drop (Simplified for this region size)
      // In a real app, this formula would come from the hydro-geology service
      const estimatedDrop = (volume_liters / 100000) * 0.1;
      const finalLevel = predictedLevel - estimatedDrop;

      console.log(`🔍 Check: Forecast=${predictedLevel}m | Drop=${estimatedDrop}m | Final=${finalLevel}m | Limit=${region.critical_water_level_m}m`);

      // C. The Decision
      if (finalLevel < region.critical_water_level_m) {
        return res.status(409).json({
          success: false,
          error: "Unsafe Yield: Extraction denied.",
          details: {
            reason: "Groundwater levels critically low.",
            predicted_level_next_7d: predictedLevel,
            impact_of_extraction: -estimatedDrop,
            critical_limit: region.critical_water_level_m,
            message: "Please reduce extraction volume or wait for recharge."
          }
        });
      }
    }
    // --- 🛡️ SAFE YIELD ENFORCEMENT END ---

    // 3. Create Log (If allowed)
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