import express from 'express';
import { logExtraction, getExtractionHistory } from './extraction.controller.js';

const router = express.Router();

router.post('/', logExtraction);
router.get('/:region_id', getExtractionHistory);

export default router;