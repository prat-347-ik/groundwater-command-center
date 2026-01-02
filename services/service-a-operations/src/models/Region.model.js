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
  created_at: { 
    type: Date, 
    default: Date.now 
  }
});

export default mongoose.model('Region', RegionSchema);