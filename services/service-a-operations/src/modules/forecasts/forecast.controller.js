import Forecast from '../../models/Forecast.model.js';

/**
 * @desc    Get 7-day forecast for a specific region
 * @route   GET /api/v1/forecasts/:regionId
 * @access  Public
 */
export const getForecastsByRegion = async (req, res, next) => {
  try {
    const { regionId } = req.params;

    // --- DEBUG FIX: Removed Date Filter ---
    // We want to see ALL forecasts available for this region to ensure
    // data is flowing, regardless of whether it's "today" or "tomorrow".
    
    const forecasts = await Forecast.find({ 
      region_id: regionId
      // forecast_date: { $gte: today }  <-- COMMENTED OUT STRICT FILTER
    })
    .sort({ forecast_date: 1 }) // Oldest first
    .limit(14);                 // Show us everything

    res.status(200).json({
      success: true,
      count: forecasts.length,
      data: forecasts
    });
  } catch (err) {
    next(err);
  }
};