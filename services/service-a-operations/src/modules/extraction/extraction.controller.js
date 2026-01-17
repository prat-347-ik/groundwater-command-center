import ExtractionLog from '../../models/ExtractionLog.model.js';
import Region from '../../models/Region.model.js';

// @desc    Log water extraction (pumping)
// @route   POST /api/v1/extraction
export const logExtraction = async (req, res, next) => {
  try {
    const { region_id, volume_liters, usage_type, timestamp } = req.body;

    // 1. Validate Region Exists
    const region = await Region.findOne({ region_id });
    if (!region) {
      const error = new Error(`Region not found: ${region_id}`);
      error.status = 404;
      throw error;
    }

    // 2. Create Log
    const log = await ExtractionLog.create({
      region_id,
      volume_liters,
      usage_type,
      timestamp: timestamp || new Date()
    });

    res.status(201).json({
      success: true,
      data: log
    });
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