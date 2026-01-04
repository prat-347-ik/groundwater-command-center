import Forecast from '../../models/Forecast.model.js';

/**
 * @desc    Get 7-day forecast for a specific region
 * @route   GET /api/v1/forecasts/:regionId
 * @access  Public
 */
export const getForecastsByRegion = async (req, res, next) => {
  try {
    const { regionId } = req.params;

    // Fetch forecasts for this region, sorted by date (Earliest -> Latest)
    // We filter for dates >= today to avoid showing stale history if needed
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const forecasts = await Forecast.find({ 
      region_id: regionId,
      forecast_date: { $gte: today } 
    })
    .sort({ forecast_date: 1 })
    .limit(14); // Limit to 2 weeks max just in case

    res.status(200).json({
      success: true,
      count: forecasts.length,
      data: forecasts
    });
  } catch (err) {
    next(err);
  }
};