import express from 'express';
import { triggerPipeline, getJobStatus } from './pipeline.controller.js';

const router = express.Router();

router.post('/trigger', triggerPipeline);
router.get('/status/:id', getJobStatus);

export default router;