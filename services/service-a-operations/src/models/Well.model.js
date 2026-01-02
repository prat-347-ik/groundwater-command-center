import mongoose from 'mongoose';
import { randomUUID } from 'crypto';

const WellSchema = new mongoose.Schema({
  well_id: {
    type: String,
    default: () => randomUUID(),
    unique: true,
    required: true,
    index: true
  },
  region_id: {
    type: String,
    required: true,
    index: true // Indexed for faster lookups of wells in a region
  },
  depth: { 
    type: Number, 
    required: true,
    min: 0 
  },
  status: {
    type: String,
    enum: ['active', 'inactive', 'maintenance'],
    default: 'active'
  }
});

export default mongoose.model('Well', WellSchema);