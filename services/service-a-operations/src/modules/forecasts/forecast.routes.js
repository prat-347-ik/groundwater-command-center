import express from 'express';
import * as forecastController from './forecast.controller.js';

const router = express.Router();

router.get('/:regionId', forecastController.getForecastsByRegion);

export default router;