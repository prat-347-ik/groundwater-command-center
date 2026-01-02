import express from 'express';
import { getSystemCounts, getRegionStats } from './stats.controller.js';

const router = express.Router();

// Global health
router.get('/counts', getSystemCounts);

// Region specific health
router.get('/regions/:id', getRegionStats);

export default router;