import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import helmet from 'helmet';
import axios from 'axios'; // Make sure to install axios: npm install axios

// Import Routes (Local Operations)
import regionRoutes from './modules/regions/region.routes.js';
import wellRoutes from './modules/wells/well.routes.js';
import readingRoutes from './modules/water-readings/water-reading.routes.js';
import statsRoutes from './modules/stats/stats.routes.js';
import forecastRoutes from './modules/forecasts/forecast.routes.js'; 
import pipelineRoutes from './modules/pipeline/pipeline.routes.js'; // <--- [NEW]
import extractionRoutes from './modules/extraction/extraction.routes.js'; // 🆕 Import
// NOTE: Rainfall is now proxied to Service C, so we don't import it locally.

const app = express();

// ==========================================
// ⚙️ Configuration
// ==========================================
// Service B: Analytics Engine (Port 8200)
const SERVICE_B_URL = process.env.SERVICE_B_URL || 'http://localhost:8200';
// Service C: Climate Intelligence (Port 8100)
const SERVICE_C_URL = process.env.SERVICE_C_URL || 'http://localhost:8100';

// ==========================================
// 🛡️ Middleware Layer
// ==========================================

app.use(helmet());

app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  credentials: true
}));

app.use(morgan('dev'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// ==========================================
// 📍 Route Layer
// ==========================================

app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'UP', 
    service: 'Service A - Operations (Gateway)', 
    port: process.env.PORT || 4000,
    timestamp: new Date() 
  });
});

// -------------------------------------------------------
// 🔀 PROXY 1: Trigger Service B (Analytics Pipeline)
// -------------------------------------------------------

// MASTER PIPELINE TRIGGER
app.post('/api/v1/pipeline/trigger', async (req, res) => {
  try {
    // FIX: Pointing to the correct endpoint exposed in app.py (/jobs/pipeline)
    const targetUrl = `${SERVICE_B_URL}/jobs/pipeline`;

    console.log(`[Proxy] 🚀 Forwarding pipeline request to ${targetUrl}`);

    // Forward the date payload
    const response = await axios.post(targetUrl, req.body);
    res.status(response.status).json(response.data);

  } catch (error) {
    console.error('❌ Pipeline Proxy Error:', error.message);
    const status = error.response ? error.response.status : 502;
    res.status(status).json({ 
      error: 'Failed to trigger Analytics Pipeline',
      details: error.response?.data || error.message 
    });
  }
});

// GRANULAR JOB TRIGGERS (Train, Forecast, Promote)
app.post('/api/v1/jobs/:jobName', async (req, res) => {
  try {
    const { jobName } = req.params;
    // Maps to Service B endpoints: /jobs/train, /jobs/forecast, etc.
    const targetUrl = `${SERVICE_B_URL}/jobs/${jobName}`;
    
    console.log(`[Proxy] 🛠️ Forwarding job ${jobName} to ${targetUrl}`);
    
    const response = await axios.post(targetUrl, req.body);
    res.status(response.status).json(response.data);
  } catch (error) {
    const status = error.response ? error.response.status : 502;
    res.status(status).json({ message: `Failed to trigger job: ${error.message}` });
  }
});

// -------------------------------------------------------
// 🔀 PROXY 2: Trigger Service C (Rainfall Data)
// -------------------------------------------------------
app.use('/api/v1/rainfall', async (req, res) => {
  try {
    // Construct target URL (Preserve query params and sub-paths)
    // Example: /api/v1/rainfall/ingest/csv -> http://localhost:8100/api/v1/rainfall/ingest/csv
    const targetPath = req.url; // path relative to mount point
    const targetUrl = `${SERVICE_C_URL}/api/v1/rainfall${targetPath}`;

    console.log(`[Proxy] 🌧️ Forwarding Rainfall request to ${targetUrl}`);

    const response = await axios({
      method: req.method,
      url: targetUrl,
      data: req.body,
      params: req.query
    });

    res.status(response.status).json(response.data);
  } catch (error) {
    console.error('❌ Rainfall Proxy Error:', error.message);
    const status = error.response ? error.response.status : 502;
    res.status(status).json({ message: 'Service C (Climate) unreachable' });
  }
});

// -------------------------------------------------------
// 🏠 Local Routes
// -------------------------------------------------------
app.use('/api/v1/regions', regionRoutes);
app.use('/api/v1/wells', wellRoutes);
app.use('/api/v1/water-readings', readingRoutes);
app.use('/api/v1/stats', statsRoutes);
app.use('/api/v1/forecasts', forecastRoutes);
app.use('/api/v1/pipeline', pipelineRoutes); // <--- []
app.use('/api/v1/extraction', extractionRoutes); // 🆕 Extraction Routes

// ==========================================
// ⚠️ Error Handling Layer
// ==========================================

app.use((req, res, next) => {
  res.status(404).json({ message: `Route not found: ${req.originalUrl}` });
});

app.use((err, req, res, next) => {
  console.error('❌ Server Error:', err.stack);
  res.status(err.status || 500).json({
    error: {
      message: err.message || 'Internal Server Error',
      status: err.status || 500
    }
  });
});

export default app;