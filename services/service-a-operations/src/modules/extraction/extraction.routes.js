import express from 'express';
import { createLog, getExtractionHistory } from './extraction.controller.js';

const router = express.Router();

router.post('/', createLog);
router.get('/:region_id', getExtractionHistory);

export default router;