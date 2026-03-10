"use client";

import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Legend } from 'recharts';
import { format } from 'date-fns';

interface WaterLevelChartProps {
  history: any[];
  forecast: any[];
  criticalLevel: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-slate-200 shadow-xl rounded-lg text-xs">
        <p className="font-bold text-slate-700 mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 mb-1 last:mb-0">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-slate-500 font-medium">{entry.name}:</span>
            <span className="text-slate-900 font-bold">{Number(entry.value).toFixed(2)}m</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function WaterLevelChart({ history, forecast, criticalLevel }: WaterLevelChartProps) {
  // Merge and Sort Data
  const data = [
    ...history.map((h: any) => ({
      date: h.timestamp,
      displayDate: format(new Date(h.timestamp), 'MMM dd'),
      historical: h.water_level,
      forecast: null
    })), 
    ...forecast.map((f: any) => ({
      date: f.forecast_date,
      displayDate: format(new Date(f.forecast_date), 'MMM dd'),
      historical: null,
      forecast: f.predicted_level
    }))
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  // Connect the lines visually (Fill the gap)
  const lastHistoryIndex = data.findLastIndex(d => d.historical !== null);
  if (lastHistoryIndex >= 0 && lastHistoryIndex < data.length - 1) {
    data[lastHistoryIndex].forecast = data[lastHistoryIndex].historical;
  }

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        <div>
          <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <span className="p-1.5 bg-blue-100 text-blue-600 rounded-lg">💧</span>
            Aquifer Health Monitor
          </h3>
          <p className="text-sm text-slate-500 mt-1 ml-9">Real-time telemetry & 7-day AI forecast</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold text-red-700 bg-red-50 px-3 py-2 rounded-lg border border-red-100">
          <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"/>
          CRITICAL THRESHOLD: {criticalLevel}m
        </div>
      </div>

      <div className="h-[350px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorHistory" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="displayDate" tick={{fontSize: 11, fill: '#64748b'}} axisLine={false} tickLine={false} dy={10} />
            <YAxis reversed={true} tick={{fontSize: 11, fill: '#64748b'}} axisLine={false} tickLine={false} unit="m" />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={criticalLevel} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Limit', fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }} />
            
            <Area 
              type="monotone" 
              dataKey="historical" 
              name="Observed Level" 
              stroke="#2563eb" 
              strokeWidth={3} 
              fill="url(#colorHistory)" 
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Area 
              type="monotone" 
              dataKey="forecast" 
              name="AI Prediction" 
              stroke="#7c3aed" 
              strokeWidth={3} 
              strokeDasharray="5 5" 
              fill="url(#colorForecast)" 
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px', fontWeight: 500 }}/>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}