import express from 'express';
import { 
  createRegion, 
  getAllRegions, 
  getRegionById, 
  updateRegion, 
  deleteRegion 
} from './region.controller.js';

const router = express.Router();

router.route('/')
  .post(createRegion)
  .get(getAllRegions);

router.route('/:id')
  .get(getRegionById)
  .put(updateRegion)
  .delete(deleteRegion);

export default router;