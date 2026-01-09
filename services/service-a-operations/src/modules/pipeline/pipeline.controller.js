import axios from 'axios';
import Job from '../../models/Job.model.js';

// Configuration for Service B (Analytics)
const SERVICE_B_URL = process.env.SERVICE_B_URL || 'http://localhost:8200';

/**
 * @desc    Trigger the Analytics Pipeline (Async)
 * @route   POST /api/v1/pipeline/trigger
 * @access  Public
 */
export const triggerPipeline = async (req, res, next) => {
  try {
    const { date, type = 'full_pipeline' } = req.body;

    // 1. Create a Job Record (State: Pending)
    const newJob = await Job.create({
      job_type: type,
      status: 'pending',
      target_date: date ? new Date(date) : new Date()
    });

    // 2. Respond to User IMMEDIATELY (202 Accepted)
    res.status(202).json({
      success: true,
      message: 'Pipeline job submitted successfully',
      job_id: newJob._id,
      status_url: `/api/v1/pipeline/status/${newJob._id}`
    });

    // 3. Perform Background Operation (Do NOT await this block)
    // We intentionally let this run in the background
    (async () => {
      try {
        // Update to 'processing'
        await Job.findByIdAndUpdate(newJob._id, { status: 'processing' });

        // Determine Service B Endpoint based on type
        let endpoint = '/jobs/pipeline';
        if (type === 'daily_summary') endpoint = '/jobs/daily-summary';
        if (type === 'training') endpoint = '/jobs/train';
        if (type === 'forecast') endpoint = '/jobs/forecast';

        // Call Service B
        const response = await axios.post(`${SERVICE_B_URL}${endpoint}`, {
          date: date
        });

        // Update Job to 'completed'
        await Job.findByIdAndUpdate(newJob._id, {
          status: 'completed',
          result: response.data,
          completed_at: new Date()
        });

      } catch (err) {
        console.error(`❌ Background Job ${newJob._id} Failed:`, err.message);
        
        // Update Job to 'failed'
        await Job.findByIdAndUpdate(newJob._id, {
          status: 'failed',
          error: err.response?.data?.detail || err.message,
          completed_at: new Date()
        });
      }
    })();

  } catch (error) {
    next(error);
  }
};

/**
 * @desc    Get status of a specific job
 * @route   GET /api/v1/pipeline/status/:id
 * @access  Public
 */
export const getJobStatus = async (req, res, next) => {
  try {
    const job = await Job.findById(req.params.id);

    if (!job) {
      const error = new Error('Job not found');
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      data: job
    });

  } catch (error) {
    next(error);
  }
};