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
  TrendingUp,
  Activity
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

  // Constants
  const MAX_EXTRACTION_LITERS = 1000000; // 1000 kL

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
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden ring-1 ring-slate-900/5 font-sans">
      
      {/* --- Header --- */}
      <div className="px-6 py-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-800 tracking-tight">Predictive Lab</h2>
          </div>
          <p className="text-xs text-slate-500 font-medium ml-1">
            Target Region: <span className="text-indigo-600 font-bold">{regionName}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => { setSchedule(Array(7).fill(0)); runSimulation(); }}
            className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors flex items-center gap-2 border border-transparent hover:border-indigo-100"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </button>
          
          <button 
            onClick={() => runSimulation()}
            disabled={loading}
            className={`
              px-6 py-2.5 rounded-lg text-sm font-bold text-white shadow-lg shadow-indigo-500/20 
              flex items-center gap-2 transition-all active:scale-95
              ${loading ? 'bg-indigo-400 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-700 hover:shadow-indigo-500/30'}
            `}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Calculating...
              </span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> Run Simulation
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        {/* --- Left Panel: Controls (Dark Theme) --- */}
        <div className="w-full lg:w-80 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden relative">
          {/* Subtle gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 to-transparent pointer-events-none" />
          
          <div className="p-5 border-b border-slate-800 bg-slate-900/50 backdrop-blur relative z-10">
            <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-1 flex items-center gap-2">
              <Droplets className="w-3 h-3" /> Extraction Schedule
            </h3>
            <p className="text-xs text-slate-400 font-medium">Adjust daily pumping volume (7-Day)</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar relative z-10">
            {schedule.map((val, i) => {
              const dayLabel = format(addDays(new Date(), i + 1), 'EEE');
              const percent = (val / MAX_EXTRACTION_LITERS) * 100;
              
              return (
                <div key={i} className="group">
                  <div className="flex justify-between items-end mb-2">
                    <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded text-center min-w-[3rem] group-hover:text-indigo-300 transition-colors">
                      {dayLabel}
                    </span>
                    <span className="text-sm font-mono font-bold text-white">
                      {(val / 1000).toFixed(0)} <span className="text-xs text-slate-500 font-sans">kL</span>
                    </span>
                  </div>
                  
                  <div className="relative h-5 flex items-center group">
                    <input 
                      type="range" 
                      min="0" max={MAX_EXTRACTION_LITERS} step="10000"
                      value={val}
                      onChange={(e) => handleSliderChange(i, Number(e.target.value))}
                      className="absolute z-20 w-full h-full opacity-0 cursor-pointer"
                    />
                    {/* Dark Track */}
                    <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden relative z-10">
                      <div 
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-150 ease-out shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    {/* Thumb Glow */}
                    <div 
                      className="absolute h-3 w-3 bg-white rounded-full shadow-lg shadow-indigo-500/50 z-10 pointer-events-none transition-all duration-150 ease-out group-hover:scale-125"
                      style={{ left: `calc(${percent}% - 6px)` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* --- Right Panel: Charts & Stats --- */}
        <div className="flex-1 flex flex-col min-h-[400px] relative bg-slate-50/50">
          
          {/* Stats Bar */}
          <div className="grid grid-cols-2 border-b border-slate-200 divide-x divide-slate-200 bg-white">
            <div className={`p-4 flex items-center gap-4 transition-colors ${isCritical ? 'bg-red-50' : ''}`}>
              <div className={`p-3 rounded-xl shadow-sm ${isCritical ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                {isCritical ? <AlertTriangle className="w-5 h-5" /> : <TrendingUp className="w-5 h-5" />}
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Aquifer Status</p>
                <p className={`text-sm font-bold ${isCritical ? 'text-red-700' : 'text-emerald-700'}`}>
                  {isCritical ? 'Critical Depletion' : 'Sustainable Levels'}
                </p>
              </div>
            </div>
            
            <div className="p-4 flex items-center gap-4 bg-white">
              <div className="p-3 rounded-xl shadow-sm bg-blue-50 text-blue-600">
                <TrendingDown className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Projected Impact</p>
                <p className="text-sm font-bold text-slate-700">
                  {Math.abs(maxDrop).toFixed(2)}m <span className="text-slate-400 font-normal">drawdown</span>
                </p>
              </div>
            </div>
          </div>

          {/* Chart Area */}
          <div className="flex-1 p-6 relative">
            {error && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/50 backdrop-blur-sm">
                <div className="text-red-600 font-medium flex items-center gap-2 bg-red-50 px-6 py-4 rounded-xl border border-red-100 shadow-xl">
                  <AlertTriangle className="w-6 h-6" /> {error}
                </div>
              </div>
            )}

            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorBase" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#64748b" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#64748b" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorScen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isCritical ? "#ef4444" : "#6366f1"} stopOpacity={0.25}/>
                    <stop offset="95%" stopColor={isCritical ? "#ef4444" : "#6366f1"} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#94a3b8', fontSize: 12, fontWeight: 500}} 
                  dy={15}
                />
                <YAxis 
                  domain={['auto', 'auto']} 
                  hide 
                />
                
                <Tooltip 
                  cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '4 4' }}
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const base = payload[0].value as number;
                      const scen = payload[1].value as number;
                      return (
                        <div className="bg-slate-900 p-4 border border-slate-800 shadow-2xl rounded-xl text-xs text-white">
                          <p className="font-bold text-slate-300 mb-3 text-sm">{payload[0].payload.fullDate}</p>
                          <div className="space-y-2">
                            <div className="flex items-center justify-between gap-6">
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-slate-500" />
                                <span className="text-slate-400">Baseline</span>
                              </div>
                              <span className="font-mono font-bold">{base.toFixed(2)}m</span>
                            </div>
                            <div className="flex items-center justify-between gap-6">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${isCritical ? 'bg-red-500' : 'bg-indigo-500'}`} />
                                <span className={isCritical ? "text-red-400" : "text-indigo-400"}>Scenario</span>
                              </div>
                              <span className={`font-mono font-bold ${isCritical ? 'text-red-400' : 'text-indigo-400'}`}>
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
                
                <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ top: -10 }} />

                <ReferenceLine 
                  y={criticalLevel} 
                  stroke="#ef4444" 
                  strokeDasharray="3 3" 
                  strokeWidth={2}
                  label={{ 
                    value: 'CRITICAL LIMIT', 
                    fill: '#ef4444', 
                    fontSize: 10, 
                    fontWeight: 700,
                    position: 'insideTopRight',
                    dy: -10 
                  }} 
                />

                <Area 
                  type="monotone" 
                  dataKey="Baseline" 
                  stroke="#94a3b8" 
                  strokeWidth={2}
                  fill="url(#colorBase)" 
                  fillOpacity={1}
                  activeDot={{ r: 4, fill: '#64748b' }}
                />
                
                <Area 
                  type="monotone" 
                  dataKey="Scenario" 
                  stroke={isCritical ? "#ef4444" : "#6366f1"} 
                  strokeWidth={3}
                  fill="url(#colorScen)" 
                  fillOpacity={1}
                  activeDot={{ r: 6, strokeWidth: 2, stroke: '#fff' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}