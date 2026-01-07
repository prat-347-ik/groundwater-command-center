'use client';

import { WaterReading, Forecast, RainfallReading } from '@/types';
import { TrendingDown, TrendingUp, Droplets, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface Props {
  history: WaterReading[];
  forecasts: Forecast[];
  rainfall: RainfallReading[];
  criticalLevel: number;
}

export default function KPIGrid({ history, forecasts, rainfall, criticalLevel }: Props) {
  // 1. Calculate Current Status
  const latestReading = history.length > 0 ? history[history.length - 1] : null;
  const currentLevel = latestReading?.water_level || 0;
  const isCritical = currentLevel <= criticalLevel;

  // 2. Calculate Total Rainfall (Last 30 Days)
  // Assuming data passed is already filtered or we sum all available
  const totalRain = rainfall.reduce((sum, r) => sum + r.amount_mm, 0);

  // 3. Calculate Trend (Next 7 Days)
  const nextForecast = forecasts.length > 0 ? forecasts[0] : null;
  const trend = nextForecast 
    ? (nextForecast.predicted_level - currentLevel) 
    : 0;
  
  const trendLabel = trend > 0 ? 'Recovering' : trend < 0 ? 'Depleting' : 'Stable';

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      
      {/* KPI 1: Aquifer Health Status */}
      <div className={`p-4 rounded-xl border flex items-center gap-4 shadow-sm
        ${isCritical ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200'}`}>
        <div className={`p-3 rounded-full ${isCritical ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
          {isCritical ? <AlertTriangle className="w-6 h-6" /> : <CheckCircle2 className="w-6 h-6" />}
        </div>
        <div>
          <p className="text-sm font-medium text-slate-500 uppercase">Current Status</p>
          <h4 className={`text-xl font-bold ${isCritical ? 'text-red-700' : 'text-emerald-700'}`}>
            {isCritical ? 'CRITICAL' : 'SAFE'}
          </h4>
          <p className="text-xs opacity-75">
            Depth: {currentLevel.toFixed(2)}m (Limit: {criticalLevel}m)
          </p>
        </div>
      </div>

      {/* KPI 2: Rainfall Accumulation */}
      <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex items-center gap-4">
        <div className="p-3 rounded-full bg-blue-50 text-blue-500">
          <Droplets className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-500 uppercase">Rainfall (Season)</p>
          <h4 className="text-xl font-bold text-slate-800">{totalRain.toFixed(1)} mm</h4>
          <p className="text-xs text-slate-400">Total recorded in dataset</p>
        </div>
      </div>

      {/* KPI 3: AI Forecast Trend */}
      <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm flex items-center gap-4">
        <div className={`p-3 rounded-full ${trend >= 0 ? 'bg-violet-50 text-violet-500' : 'bg-orange-50 text-orange-500'}`}>
          {trend >= 0 ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
        </div>
        <div>
          <p className="text-sm font-medium text-slate-500 uppercase">7-Day AI Trend</p>
          <h4 className="text-xl font-bold text-slate-800">{trendLabel}</h4>
          <p className="text-xs text-slate-400">
            Expected change: {trend > 0 ? '+' : ''}{trend.toFixed(2)}m
          </p>
        </div>
      </div>

    </div>
  );
}