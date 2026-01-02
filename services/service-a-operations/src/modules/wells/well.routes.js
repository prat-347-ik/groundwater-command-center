import express from 'express';
import { 
  createWell, 
  getWellsByRegion,
  getWellById,
  updateWell
} from './well.controller.js';

const router = express.Router({ mergeParams: true }); 
// mergeParams is crucial if we mount this route under /regions/:regionId later

// Route: /api/v1/wells
router.route('/')
  .post(createWell);

// Route: /api/v1/wells/:id
router.route('/:id')
  .get(getWellById)
  .put(updateWell);

// Route: /api/v1/regions/:regionId/wells
// Note: This endpoint is strictly for fetching wells relative to a region
router.route('/regions/:regionId/wells')
  .get(getWellsByRegion);

export default router;