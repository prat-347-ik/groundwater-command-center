import mongoose from 'mongoose';

const ExtractionSchema = new mongoose.Schema({
  region_id: { 
    type: String, 
    required: true,
    index: true // Indexed for fast queries by region
  },
  volume_liters: { 
    type: Number, 
    required: true,
    min: 0 
  },
  usage_type: { 
    type: String,
    enum: ['irrigation', 'industrial', 'domestic'], 
    required: true 
  },
  timestamp: { 
    type: Date, 
    default: Date.now,
    index: true // Indexed for time-series aggregation
  }
});

export default mongoose.model('ExtractionLog', ExtractionSchema);