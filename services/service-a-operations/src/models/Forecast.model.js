import mongoose from 'mongoose';

const ForecastSchema = new mongoose.Schema({
  region_id: { 
    type: String, 
    required: true, 
    index: true 
  },
  forecast_date: { 
    type: Date, 
    required: true 
  },
  predicted_level: { 
    type: Number, 
    required: true 
  },
  model_version: { 
    type: String 
  },
  horizon_step: { 
    type: Number 
  },
  created_at: { 
    type: Date, 
    default: Date.now 
  }
}, {
  // ⚠️ CRITICAL: Must match the collection name used by Service B (Analytics)
  collection: 'daily_forecasts',
  timestamps: false // Service B manages its own timestamps
});

export default mongoose.model('Forecast', ForecastSchema);  