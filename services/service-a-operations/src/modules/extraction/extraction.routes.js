import express from 'express';
import { createLog, getExtractionHistory, getExtractionHistoryByRegion} from './extraction.controller.js';

const router = express.Router();

router.post('/', createLog);
router.get('/:region_id', getExtractionHistory);
router.get('/region/:regionId', getExtractionHistoryByRegion);

export default router;