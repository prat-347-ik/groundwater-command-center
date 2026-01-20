"use client";

import { useState } from 'react'; // ✅ Valid (React is a core dependency)
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'; //  Valid (Assuming `recharts` is installed in `package.json`)
import { Play, RotateCcw, AlertTriangle, Droplets } from 'lucide-react'; //  Valid (Assuming `lucide-react` is installed in `package.json`)
import { analyticsClient } from '@/lib/api'; //  Check if `frontend/src/lib/api.ts` exists and exports `analyticsClient`
import { Forecast } from '@/types'; //  Check if `frontend/src/types/index.ts` (or similar) exists and exports `Forecast`
import { format, addDays } from 'date-fns'; // Valid (Assuming `date-fns` is installed in `package.json`)

interface SimulationLabProps {
  regionId: string;
  regionName: string;
  criticalLevel: number;
}

export default function SimulationLab({ regionId, regionName, criticalLevel }: SimulationLabProps) {
  // State for the 7-day extraction schedule (in Liters)
  const [schedule, setSchedule] = useState<number[]>([0, 0, 0, 0, 0, 0, 0]);
  const [scenarioResults, setScenarioResults] = useState<Forecast[]>([]);
  const [baselineResults, setBaselineResults] = useState<Forecast[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper: Handle slider change for a specific day
  const handleSliderChange = (index: number, value: number) => {
    const newSchedule = [...schedule];
    newSchedule[index] = value;
    setSchedule(newSchedule);
  };

  // Helper: Run the simulation
  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch Baseline (Business as Usual - 0 Extraction)
      // Note: In a real app, you might cache this or fetch it once on mount.
      const baselineRes = await analyticsClient.post('/forecasts/generate', {
        region_id: regionId,
        planned_extraction: [0, 0, 0, 0, 0, 0, 0] // Zero extraction baseline
      });

      // 2. Fetch Scenario (User Input)
      const scenarioRes = await analyticsClient.post('/forecasts/generate', {
        region_id: regionId,
        planned_extraction: schedule
      });

      setBaselineResults(baselineRes.data.data);
      setScenarioResults(scenarioRes.data.data);
    } catch (err: any) {
      console.error("Simulation Failed", err);
      setError("Failed to run simulation. Is Service B online?");
    } finally {
      setLoading(false);
    }
  };

  // Helper: Merge data for the chart
  const chartData = baselineResults.map((baseItem, idx) => {
    const scenarioItem = scenarioResults[idx];
    return {
      date: format(new Date(baseItem.forecast_date), 'MMM dd'),
      baseline: baseItem.predicted_level,
      scenario: scenarioItem ? scenarioItem.predicted_level : null,
      critical: criticalLevel
    };
  });

  // Check for critical breaches
  const isCritical = scenarioResults.some(f => f.predicted_level < criticalLevel);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Droplets className="text-blue-600 h-5 w-5" />
            Simulation Lab: {regionName}
          </h2>
          <p className="text-sm text-slate-500">
            Adjust daily extraction to predict impact.
          </p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => setSchedule([0,0,0,0,0,0,0])}
            className="p-2 text-slate-500 hover:bg-slate-200 rounded-lg transition-colors"
            title="Reset"
          >
            <RotateCcw className="h-5 w-5" />
          </button>
          <button 
            onClick={runSimulation}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50"
          >
            {loading ? 'Simulating...' : <><Play className="h-4 w-4" /> Run Scenario</>}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 h-full">
        {/* Left: Controls */}
        <div className="p-6 border-r border-slate-100 bg-slate-50/50 overflow-y-auto">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wider">
            7-Day Extraction Plan
          </h3>
          <div className="space-y-6">
            {schedule.map((liters, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between text-xs text-slate-600">
                  <span className="font-medium">
                    Day {i + 1} ({format(addDays(new Date(), i + 1), 'EEE')})
                  </span>
                  <span className="text-blue-600 font-bold">
                    {(liters / 1000).toFixed(1)}k Liters
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100000" // Cap at 100k Liters for UI demo
                  step="1000"
                  value={liters}
                  onChange={(e) => handleSliderChange(i, Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Right: Visualization */}
        <div className="lg:col-span-2 p-6 flex flex-col">
          {error ? (
            <div className="flex-1 flex items-center justify-center text-red-500 bg-red-50 rounded-lg border border-red-100">
              <AlertTriangle className="mr-2 h-5 w-5" /> {error}
            </div>
          ) : scenarioResults.length > 0 ? (
            <div className="flex-1 min-h-[400px]">
              {isCritical && (
                <div className="mb-4 p-3 bg-red-100 border border-red-200 text-red-800 rounded-md flex items-center text-sm">
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Warning: Scenario breaches critical water level of {criticalLevel}m!
                </div>
              )}
              
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fill: '#64748b', fontSize: 12}} 
                    dy={10}
                  />
                  <YAxis 
                    domain={['auto', 'auto']} 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fill: '#64748b', fontSize: 12}} 
                    label={{ value: 'Water Level (m)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                  />
                  <Tooltip 
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                  />
                  <Legend verticalAlign="top" height={36}/>
                  
                  {/* Baseline (Business as Usual) */}
                  <Line 
                    type="monotone" 
                    dataKey="baseline" 
                    name="Baseline (0L)" 
                    stroke="#94a3b8" 
                    strokeWidth={2} 
                    strokeDasharray="5 5" 
                    dot={false} 
                  />
                  
                  {/* Scenario (What-If) */}
                  <Line 
                    type="monotone" 
                    dataKey="scenario" 
                    name="Scenario Impact" 
                    stroke={isCritical ? "#ef4444" : "#2563eb"} 
                    strokeWidth={3} 
                    activeDot={{ r: 6 }} 
                  />

                  {/* Critical Limit Line */}
                  <ReferenceLine 
                    y={criticalLevel} 
                    label="Critical Limit" 
                    stroke="#ef4444" 
                    strokeDasharray="3 3" 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
              <RotateCcw className="h-8 w-8 mb-2 opacity-50" />
              <p>Adjust extraction sliders and click Run Scenario</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}