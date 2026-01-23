"use client";

import { useState, useEffect } from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { 
  Play, 
  RotateCcw, 
  AlertTriangle, 
  Droplets, 
  TrendingDown, 
  TrendingUp 
} from 'lucide-react';
import { analyticsClient } from '@/lib/api';
import { format, addDays } from 'date-fns';

interface Forecast {
  region_id: string;
  forecast_date: string;
  predicted_level: number;
  horizon_step: number;
}

interface SimulationLabProps {
  regionId: string;
  regionName: string;
  criticalLevel: number;
}

export default function SimulationLab({ regionId, regionName, criticalLevel }: SimulationLabProps) {
  // 7-Day Schedule State (Values in Liters)
  const [schedule, setSchedule] = useState<number[]>([0, 0, 0, 0, 0, 0, 0]);
  
  // Results State
  const [baseline, setBaseline] = useState<Forecast[]>([]);
  const [scenario, setScenario] = useState<Forecast[]>([]);
  
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize: Run baseline once on mount
  useEffect(() => {
    if (regionId && !hasRun) {
      runSimulation(true); 
    }
  }, [regionId]);

  const handleSliderChange = (index: number, value: number) => {
    const newSchedule = [...schedule];
    newSchedule[index] = value;
    setSchedule(newSchedule);
  };

  const runSimulation = async (isInit = false) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Always fetch Baseline (Zero Extraction) to compare
      const baseReq = analyticsClient.post('/forecasts/generate', {
        region_id: regionId,
        planned_extraction: [0, 0, 0, 0, 0, 0, 0]
      });

      // 2. Fetch Scenario (User Schedule)
      const scenReq = analyticsClient.post('/forecasts/generate', {
        region_id: regionId,
        planned_extraction: schedule
      });

      const [baseRes, scenRes] = await Promise.all([baseReq, scenReq]);

      setBaseline(baseRes.data.data);
      setScenario(scenRes.data.data);
      setHasRun(true);
    } catch (err: any) {
      console.error("Simulation Error:", err);
      setError("Simulation service unavailable.");
    } finally {
      setLoading(false);
    }
  };

  // Merge Data for Chart
  const chartData = baseline.map((bItem, i) => {
    const sItem = scenario[i];
    return {
      date: format(new Date(bItem.forecast_date), 'MMM dd'),
      fullDate: format(new Date(bItem.forecast_date), 'EEEE, MMM dd'),
      Baseline: bItem.predicted_level,
      Scenario: sItem?.predicted_level || bItem.predicted_level,
      delta: (sItem?.predicted_level || 0) - bItem.predicted_level
    };
  });

  // Analysis
  const isCritical = chartData.some(d => d.Scenario < criticalLevel);
  const maxDrop = Math.min(...chartData.map(d => d.delta)); // Biggest negative number

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden ring-1 ring-slate-900/5">
      
      {/* --- Header --- */}
      <div className="px-6 py-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-50 to-white">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">
              <Droplets className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-800 tracking-tight">Simulation Lab</h2>
          </div>
          <p className="text-sm text-slate-500 font-medium">
            Projecting impact for <span className="text-slate-800">{regionName}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => { setSchedule(Array(7).fill(0)); runSimulation(); }}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" /> Reset
          </button>
          
          <button 
            onClick={() => runSimulation()}
            disabled={loading}
            className={`
              px-6 py-2.5 rounded-lg text-sm font-bold text-white shadow-lg shadow-blue-500/30 
              flex items-center gap-2 transition-all active:scale-95
              ${loading ? 'bg-blue-400 cursor-wait' : 'bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/40'}
            `}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Run Scenario
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        {/* --- Left Panel: Controls --- */}
        <div className="w-full lg:w-80 bg-slate-50 border-r border-slate-100 flex flex-col overflow-hidden">
          <div className="p-5 border-b border-slate-200/60 bg-white">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Input Parameters</h3>
            <p className="text-sm text-slate-600 font-medium">Daily Extraction Plan (7 Days)</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
            {schedule.map((val, i) => {
              const dayLabel = format(addDays(new Date(), i + 1), 'EEE');
              const percent = (val / 100000) * 100;
              
              return (
                <div key={i} className="group">
                  <div className="flex justify-between items-end mb-2">
                    <span className="text-xs font-bold text-slate-500 bg-slate-200 px-2 py-0.5 rounded text-center min-w-[3rem]">
                      {dayLabel}
                    </span>
                    <span className="text-sm font-mono font-bold text-blue-600">
                      {(val / 1000).toFixed(1)} <span className="text-xs text-slate-400 font-sans">kL</span>
                    </span>
                  </div>
                  
                  <div className="relative h-6 flex items-center">
                    <input 
                      type="range" 
                      min="0" max="100000" step="1000"
                      value={val}
                      onChange={(e) => handleSliderChange(i, Number(e.target.value))}
                      className="absolute z-20 w-full h-full opacity-0 cursor-pointer"
                    />
                    {/* Custom Track */}
                    <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden relative z-10">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-150 ease-out"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    {/* Thumb Indicator (Visual only) */}
                    <div 
                      className="absolute h-4 w-4 bg-white border-2 border-blue-500 rounded-full shadow-md z-10 pointer-events-none transition-all duration-150 ease-out"
                      style={{ left: `calc(${percent}% - 8px)` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* --- Right Panel: Charts & Stats --- */}
        <div className="flex-1 flex flex-col min-h-[400px] relative bg-white">
          
          {/* Stats Bar */}
          <div className="grid grid-cols-2 border-b border-slate-100 divide-x divide-slate-100">
            <div className={`p-4 flex items-center gap-3 ${isCritical ? 'bg-red-50/50' : 'bg-emerald-50/50'}`}>
              <div className={`p-2 rounded-full ${isCritical ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                {isCritical ? <AlertTriangle className="w-5 h-5" /> : <TrendingUp className="w-5 h-5" />}
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase">Status</p>
                <p className={`text-sm font-bold ${isCritical ? 'text-red-700' : 'text-emerald-700'}`}>
                  {isCritical ? 'Critical Breach' : 'Sustainable'}
                </p>
              </div>
            </div>
            
            <div className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-full bg-indigo-100 text-indigo-600">
                <TrendingDown className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase">Max Impact</p>
                <p className="text-sm font-bold text-slate-700">
                  {maxDrop.toFixed(2)}m <span className="text-slate-400 font-normal">vs baseline</span>
                </p>
              </div>
            </div>
          </div>

          {/* Chart Area */}
          <div className="flex-1 p-6 relative">
            {error && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80 backdrop-blur-sm">
                <div className="text-red-500 font-medium flex items-center gap-2 bg-red-50 px-4 py-2 rounded-lg border border-red-100">
                  <AlertTriangle className="w-5 h-5" /> {error}
                </div>
              </div>
            )}

            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorBase" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorScen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isCritical ? "#ef4444" : "#3b82f6"} stopOpacity={0.2}/>
                    <stop offset="95%" stopColor={isCritical ? "#ef4444" : "#3b82f6"} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94a3b8', fontSize: 12}} 
                  dy={10}
                />
                <YAxis 
                  domain={['auto', 'auto']} 
                  hide // Hide Y Axis for cleaner look, tooltip handles values
                />
                
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const base = payload[0].value as number;
                      const scen = payload[1].value as number;
                      return (
                        <div className="bg-white p-3 border border-slate-100 shadow-xl rounded-xl text-sm">
                          <p className="font-bold text-slate-800 mb-2">{payload[0].payload.fullDate}</p>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full bg-slate-400" />
                              <span className="text-slate-500">Baseline:</span>
                              <span className="font-mono font-bold text-slate-700">{base.toFixed(2)}m</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full ${isCritical ? 'bg-red-500' : 'bg-blue-500'}`} />
                              <span className={isCritical ? "text-red-600" : "text-blue-600"}>Scenario:</span>
                              <span className={`font-mono font-bold ${isCritical ? 'text-red-600' : 'text-blue-600'}`}>
                                {scen.toFixed(2)}m
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                
                <Legend verticalAlign="top" height={36} iconType="circle" />

                <ReferenceLine 
                  y={criticalLevel} 
                  stroke="#ef4444" 
                  strokeDasharray="3 3" 
                  label={{ value: 'Critical Level', fill: '#ef4444', fontSize: 12, position: 'insideTopRight' }} 
                />

                <Area 
                  type="monotone" 
                  dataKey="Baseline" 
                  stroke="#94a3b8" 
                  strokeWidth={2}
                  fill="url(#colorBase)" 
                  fillOpacity={1}
                  activeDot={{ r: 4 }}
                />
                
                <Area 
                  type="monotone" 
                  dataKey="Scenario" 
                  stroke={isCritical ? "#ef4444" : "#3b82f6"} 
                  strokeWidth={3}
                  fill="url(#colorScen)" 
                  fillOpacity={1}
                  activeDot={{ r: 6, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}