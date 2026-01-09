import mongoose from 'mongoose';

const JobSchema = new mongoose.Schema({
  job_type: {
    type: String,
    required: true,
    enum: ['daily_summary', 'training', 'forecast', 'full_pipeline']
  },
  status: {
    type: String,
    required: true,
    enum: ['pending', 'processing', 'completed', 'failed'],
    default: 'pending'
  },
  target_date: {
    type: Date
  },
  result: {
    type: mongoose.Schema.Types.Mixed, // Store generic JSON result
    default: null
  },
  error: {
    type: String,
    default: null
  },
  created_at: {
    type: Date,
    default: Date.now
  },
  completed_at: {
    type: Date
  }
});

export default mongoose.model('Job', JobSchema);