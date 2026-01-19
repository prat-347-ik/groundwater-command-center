import mongoose from 'mongoose';
import { randomUUID } from 'crypto';

const RegionSchema = new mongoose.Schema({
  region_id: {
    type: String,
    default: () => randomUUID(),
    unique: true,
    required: true,
    index: true
  },
  name: { 
    type: String, 
    required: true,
    trim: true
  },
  state: { 
    type: String, 
    required: true 
  },
  critical_level: { 
    type: Number, 
    required: true,
    min: 0
  },
  is_active: {
    type: Boolean,
    default: true,
    index: true // Indexed for filtering active regions quickly
  },

  // 🆕 NEW FIELD: The "Red Line"
  critical_water_level_m: {
    type: Number,
    default: 10.0, // If water drops below 10m, stop all pumping
    required: true
  }, // <--- FIXED: Added missing comma here

  created_at: { 
    type: Date, 
    default: Date.now 
  }
}, { timestamps: true }); // <--- FIXED: Options object is now the second argument

export default mongoose.model('Region', RegionSchema);