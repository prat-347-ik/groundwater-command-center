import express from 'express';
import multer from 'multer';
import { 
  createRainfall, 
  ingestRainfallCSV, 
  getRainfall, 
  getRainfallStats 
} from './rainfall.controller.js';

const router = express.Router();

// Configure Multer (Temp storage for CSV uploads)
const upload = multer({ dest: 'uploads/' });

// ==========================================
// 🌧️ Rainfall Endpoints
// ==========================================

// 1. Get Rainfall Data (with filters: region_id, from, to)
// GET /api/v1/rainfall
router.get('/', getRainfall);

// 2. Manual Entry (Single Record)
// POST /api/v1/rainfall
router.post('/', createRainfall);

// 3. Bulk Ingestion (CSV)
// POST /api/v1/rainfall/ingest/csv
// Key for file upload must be 'file'
router.post('/ingest/csv', upload.single('file'), ingestRainfallCSV);

// 4. Admin Stats (Debug)
// GET /api/v1/rainfall/stats
router.get('/stats', getRainfallStats);

export default router;