"use client";

import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import { format, parseISO } from 'date-fns';

interface UnifiedChartProps {
  history: any[];
  forecast: any[];
  rainfall?: any[]; 
  criticalLevel: number;
}

// 🎨 Custom Tooltip Component
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-slate-200 shadow-xl rounded-lg ring-1 ring-slate-100">
        <p className="text-sm font-bold text-slate-700 mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-xs font-medium">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-slate-500">{entry.name}:</span>
            <span className="text-slate-900">
              {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
              {entry.unit}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function UnifiedChart({ history, forecast, rainfall = [], criticalLevel }: UnifiedChartProps) {
  
  const dataMap = new Map();

  const getEntry = (dateStr: string) => {
    if (!dateStr) return null;
    // Robust date parsing handles both "2024-01-01" and ISO strings
    const key = format(new Date(dateStr), 'yyyy-MM-dd');
    
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

  history.forEach(item => {
    const entry = getEntry(item.timestamp);
    if(entry) entry.historical = item.water_level;
  });

  forecast.forEach(item => {
    const entry = getEntry(item.forecast_date);
    if(entry) entry.forecast = item.predicted_level;
  });

  rainfall.forEach(item => {
    const entry = getEntry(item.timestamp || item.date); 
    if(entry && item.amount_mm !== undefined) {
      entry.rainfall = item.amount_mm;        
    }
  });

  let combinedData = Array.from(dataMap.values()).sort((a, b) => 
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  // 🔌 CONNECT THE LINES: Fill gap between History and Forecast
  // If we have history but no forecast for a day, and the NEXT day is forecast...
  // (Simplified approach: Simply allow Recharts to connect dots if needed, 
  // but better to explicitly set the last history point as the start of forecast line)
  const lastHistoryIndex = combinedData.findLastIndex(d => d.historical !== null);
  if (lastHistoryIndex >= 0 && lastHistoryIndex < combinedData.length - 1) {
    // Copy the last historical value to the forecast field of the same day
    // This makes the forecast line start exactly where history ends
    combinedData[lastHistoryIndex].forecast = combinedData[lastHistoryIndex].historical;
  }

  return (
    <div className="h-[400px] md:h-[450px] w-full bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700">Hydrological Correlation</h3>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
          Critical Limit: {criticalLevel}m
        </div>
      </div>
      
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={combinedData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          
          <XAxis 
            dataKey="displayDate" 
            tick={{fontSize: 11, fill: '#64748b'}} 
            tickLine={false}
            axisLine={false}
            dy={10}
          />
          
          <YAxis 
            yAxisId="left"
            tick={{fontSize: 11, fill: '#64748b'}}
            tickLine={false}
            axisLine={false}
            reversed={true} 
            unit="m"
          />

          <YAxis 
            yAxisId="right" 
            orientation="right" 
            tick={{fontSize: 11, fill: '#94a3b8'}}
            tickLine={false}
            axisLine={false}
            unit="mm"
          />

          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={36} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '12px' }}/>

          <ReferenceLine yAxisId="left" y={criticalLevel} stroke="#ef4444" strokeDasharray="3 3" />

          <Bar 
            yAxisId="right" 
            dataKey="rainfall" 
            name="Rainfall" 
            fill="#cbd5e1" 
            barSize={12}
            radius={[2, 2, 0, 0]}
          />

          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="historical" 
            name="Observed" 
            stroke="#2563eb" 
            strokeWidth={2.5} 
            dot={false}
            activeDot={{ r: 6 }}
          />

          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="forecast" 
            name="AI Forecast" 
            stroke="#7c3aed" 
            strokeWidth={2.5} 
            strokeDasharray="4 4"
            dot={false}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}