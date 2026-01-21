"use client";

import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import { format } from 'date-fns';

interface UnifiedChartProps {
  history: any[];
  forecast: any[];
  rainfall?: any[]; // 👈 New Prop
  criticalLevel: number;
}

export default function UnifiedChart({ history, forecast, rainfall = [], criticalLevel }: UnifiedChartProps) {
  
  // 1. Merge all data sources by Date
  // We create a map where keys are dates (YYYY-MM-DD) to merge efficiently
  const dataMap = new Map();

  // Helper to init date entry
  const getEntry = (dateStr: string) => {
    const key = dateStr.split('T')[0]; // Simple YYYY-MM-DD key
    if (!dataMap.has(key)) {
      dataMap.set(key, { 
        date: key, 
        displayDate: format(new Date(key), 'MMM dd'),
        historical: null, 
        forecast: null,
        rainfall: null 
      });
    }
    return dataMap.get(key);
  };

  // Process History
  history.forEach(item => {
    const entry = getEntry(item.timestamp);
    entry.historical = item.water_level;
  });

  // Process Forecast
  forecast.forEach(item => {
    const entry = getEntry(item.forecast_date);
    entry.forecast = item.predicted_level;
  });

// Process Rainfall
  rainfall.forEach(item => {
    // ❌ WAS: const entry = getEntry(item.date);
    // ❌ WAS: entry.rainfall = item.mm;
    
    // ✅ CORRECT:
    if (item.timestamp && item.amount_mm !== undefined) {
      const entry = getEntry(item.timestamp); 
      entry.rainfall = item.amount_mm;        
    }
  });
  // Convert map to sorted array
  const combinedData = Array.from(dataMap.values()).sort((a, b) => 
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  return (
    <div className="h-[450px] w-full bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="text-sm font-bold text-slate-700 mb-4">Hydrological Correlation</h3>
      
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={combinedData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          
          <XAxis dataKey="displayDate" tick={{fontSize: 12}} />
          
          {/* Left Axis: Groundwater Depth (m) */}
          <YAxis 
            yAxisId="left"
            label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft' }} 
            domain={['auto', 'auto']}
            reversed={true} // Groundwater is deeper as number gets bigger
          />

          {/* Right Axis: Rainfall (mm) */}
          <YAxis 
            yAxisId="right" 
            orientation="right" 
            label={{ value: 'Rainfall (mm)', angle: 90, position: 'insideRight' }}
          />

          <Tooltip 
            labelStyle={{ color: '#64748b' }}
            itemStyle={{ fontSize: 14 }}
            formatter={(value: number | undefined) => value !== undefined ? value.toFixed(2) : 'N/A'}
          />
          <Legend verticalAlign="top" height={36}/>

          <ReferenceLine yAxisId="left" y={criticalLevel} stroke="#ef4444" strokeDasharray="3 3" label="Critical" />

          {/* Rainfall Bars (Blue-ish gray) */}
          <Bar 
            yAxisId="right" 
            dataKey="rainfall" 
            name="Rainfall (mm)" 
            fill="#94a3b8" 
            opacity={0.3} 
            barSize={20}
          />

          {/* Historical Line */}
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="historical" 
            name="Observed Level" 
            stroke="#2563eb" 
            strokeWidth={3} 
            dot={false}
          />

          {/* Forecast Line */}
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="forecast" 
            name="AI Forecast" 
            stroke="#7c3aed" 
            strokeWidth={3} 
            strokeDasharray="5 5"
            dot={{ r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}