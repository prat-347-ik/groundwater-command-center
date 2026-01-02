import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import helmet from 'helmet';

// Import Routes (Placeholders)
// import regionRoutes from './modules/regions/region.routes.js'; // Note the .js extension!
import regionRoutes from './modules/regions/region.routes.js';
import wellRoutes from './modules/wells/well.routes.js';
import readingRoutes from './modules/water-readings/water-reading.routes.js';
import statsRoutes from './modules/stats/stats.routes.js';
import rainfallRoutes from './modules/rainfall/rainfall.routes.js';

const app = express();

// ==========================================
// 🛡️ Middleware Layer
// ==========================================

// 1. Security Headers
app.use(helmet());


// 2. Cross-Origin Resource Sharing (Allow Frontend)
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  credentials: true
}));

// 3. HTTP Request Logging
app.use(morgan('dev'));

// 4. Body Parsing
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

// Mount Routes
app.use('/api/v1/regions', regionRoutes);
app.use('/api/v1/wells', wellRoutes);     // Registers POST /wells and others
app.use('/api/v1/water-readings', readingRoutes);
app.use('/api/v1/stats', statsRoutes);
app.use('/api/v1/rainfall', rainfallRoutes);

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