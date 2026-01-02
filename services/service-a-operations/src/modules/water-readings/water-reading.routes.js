import express from 'express';
import multer from 'multer';
import { 
  createReading, 
  ingestReadingsCSV,
  getReadingsByWell,
  getReadings // 👈 Import the new function
} from './water-reading.controller.js';

const router = express.Router();

// 1. Dashboard Data Endpoint (Flexible Search)
// GET /api/v1/water-readings?region_id=...&from=...
router.get('/', getReadings);

// Configure Multer (Temp storage)
const upload = multer({ dest: 'uploads/' });

// 1. Single Insert
router.post('/', createReading);

// 2. CSV Bulk Ingestion
// 'file' matches the form-data key in Postman
router.post('/ingest/csv', upload.single('file'), ingestReadingsCSV);

// 3. Verification Route
router.get('/wells/:wellId', getReadingsByWell);

export default router;