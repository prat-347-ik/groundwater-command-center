import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import helmet from 'helmet';

// Import Routes
import regionRoutes from './modules/regions/region.routes.js';
import wellRoutes from './modules/wells/well.routes.js';
import readingRoutes from './modules/water-readings/water-reading.routes.js';
import statsRoutes from './modules/stats/stats.routes.js';
import rainfallRoutes from './modules/rainfall/rainfall.routes.js';
import forecastRoutes from './modules/forecasts/forecast.routes.js'; 

const app = express();

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
    service: 'Service A - Operational', 
    timestamp: new Date() 
  });
});

// -------------------------------------------------------
// 🔀 PROXY ROUTE: Trigger Service C (ML Pipeline)
// -------------------------------------------------------
app.post('/api/v1/pipeline/trigger', async (req, res, next) => {
  try {
    // Defines where Service C lives (Default to 8100 as fixed previously)
    const SERVICE_C_URL = process.env.SERVICE_C_URL || 'http://localhost:8200';

    console.log(`[Proxy] Forwarding trigger request to ${SERVICE_C_URL}/pipeline/trigger`);

    // Server-to-Server fetch (Bypasses CORS)
    const response = await fetch(`${SERVICE_C_URL}/pipeline/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Orchestrator responded with status ${response.status}`);
    }

    const data = await response.json();
    res.status(200).json(data);

  } catch (error) {
    console.error('❌ Proxy Error:', error.message);
    res.status(502).json({ 
      error: 'Failed to trigger ML pipeline via Service A proxy',
      details: error.message 
    });
  }
});

// Mount Standard Routes
app.use('/api/v1/regions', regionRoutes);
app.use('/api/v1/wells', wellRoutes);
app.use('/api/v1/water-readings', readingRoutes);
app.use('/api/v1/stats', statsRoutes);
app.use('/api/v1/rainfall', rainfallRoutes);
app.use('/api/v1/forecasts', forecastRoutes);

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