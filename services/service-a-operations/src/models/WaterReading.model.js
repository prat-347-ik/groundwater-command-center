import mongoose from 'mongoose';

const WaterReadingSchema = new mongoose.Schema({
  well_id: {
    type: String, // Reference to Well UUID
    required: true
  },
  region_id: {
    type: String, // Reference to Region UUID (Denormalized for query speed)
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
  }
});

// 📌 RULE: Compound Index for efficient time-range queries per region
// Example Query: "Give me all readings for Region X in the last 30 days"
WaterReadingSchema.index({ region_id: 1, timestamp: -1 });

export default mongoose.model('WaterReading', WaterReadingSchema);