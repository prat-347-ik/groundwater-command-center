import mongoose from 'mongoose';

const RainfallSchema = new mongoose.Schema({
  region_id: {
    type: String, // Reference to Region UUID (No embedding, just the ID)
    required: true,
    index: true // Simple index for basic filtering
  },
  timestamp: { 
    type: Date, 
    default: Date.now,
    required: true 
  },
  amount_mm: { 
    type: Number, // Rainfall in millimeters
    required: true,
    min: 0
  },
  source: {
    type: String,
    enum: ['sensor', 'manual', 'weather_station', 'third_party_api'],
    default: 'sensor'
  }
});

// 📌 RULE: Compound Index for efficient time-range queries per region
// Example Query: "Get total rainfall for Region X in the last 7 days"
RainfallSchema.index({ region_id: 1, timestamp: -1 });

export default mongoose.model('Rainfall', RainfallSchema);