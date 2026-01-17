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
  // --- 🆕 Phase 1: Hydro-Geological Context ---
  soil_type: { 
    type: String, 
    enum: ['clay', 'sandy_loam', 'silt', 'rock'],
    default: 'sandy_loam',
    required: true
  },
  aquifer_depth: { 
    type: Number, 
    min: 0,
    default: 50, // Default depth in meters if unknown
    required: true
  },
  permeability_index: { 
    type: Number, 
    min: 0, 
    max: 1, 
    default: 0.5, // 0 = Impermeable, 1 = Highly Permeable
    required: true
  },
  // ---------------------------------------------
  is_active: {
    type: Boolean,
    default: true,
    index: true
  },
  created_at: { 
    type: Date, 
    default: Date.now 
  }
});

export default mongoose.model('Region', RegionSchema);