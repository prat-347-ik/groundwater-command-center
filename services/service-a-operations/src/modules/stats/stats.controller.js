import Region from '../../models/Region.model.js';
import Well from '../../models/Well.model.js';
import WaterReading from '../../models/WaterReading.model.js';

// @desc    Get global system counts (Sanity Check)
// @route   GET /api/v1/stats/counts
export const getSystemCounts = async (req, res, next) => {
  try {
    // Run queries in parallel for speed
    const [regionCount, wellCount, readingCount] = await Promise.all([
      Region.countDocuments(),
      Well.countDocuments(),
      WaterReading.countDocuments()
    ]);

    res.status(200).json({
      success: true,
      timestamp: new Date(),
      counts: {
        regions: regionCount,
        wells: wellCount,
        readings: readingCount
      }
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get deep stats for a specific region
// @route   GET /api/v1/stats/regions/:id
export const getRegionStats = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 1. Check Region
    const region = await Region.findOne({ region_id: id });
    if (!region) {
      const error = new Error('Region not found');
      error.status = 404;
      throw error;
    }

    // 2. Aggregate Data
    const wellCount = await Well.countDocuments({ region_id: id });
    const readingCount = await WaterReading.countDocuments({ region_id: id });
    
    // 3. Get latest activity (Helpful for debugging ingestion order)
    const lastReading = await WaterReading.findOne({ region_id: id })
      .sort({ timestamp: -1 })
      .select('timestamp water_level well_id');

    res.status(200).json({
      success: true,
      region: {
        name: region.name,
        is_active: region.is_active
      },
      stats: {
        total_wells: wellCount,
        total_readings: readingCount,
        last_activity: lastReading ? lastReading.timestamp : 'Never'
      }
    });

  } catch (error) {
    next(error);
  }
};