import mongoose from 'mongoose';

const WaterReadingSchema = new mongoose.Schema({
  well_id: {
    type: String, // Reference to Well UUID
    required: true
  },
  region_id: {
    type: String, // Reference to Region UUID
    required: true
  },
  timestamp: { 
    type: Date, 
    default: Date.now,
    required: true 
  },
  water_level: { 
    type: Number, 
    required: true 
  },
  source: {
    type: String,
    enum: ['sensor', 'manual', 'satellite'],
    required: true
  },
  // 🆕 ANOMALY DETECTION FIELDS
  is_suspicious: {
    type: Boolean,
    default: false,
    index: true // Index this so the ML pipeline can quickly filter "clean" data
  },
  anomaly_reason: {
    type: String,
    default: null
  }
});



// Compound Index for efficient time-range queries per region
WaterReadingSchema.index({ region_id: 1, timestamp: -1 });

export default mongoose.model('WaterReading', WaterReadingSchema);