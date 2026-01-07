'use client';

import { 
  ComposedChart, 
  Line, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer, 
  ReferenceLine 
} from 'recharts';
import { format, parseISO, isValid } from 'date-fns';
import { WaterReading, Forecast, RainfallReading } from '@/types';

interface Props {
  history: WaterReading[];
  forecasts: Forecast[];
  rainfall: RainfallReading[];
  criticalLevel: number;
}

export default function HydroComboChart({ history, forecasts, rainfall, criticalLevel }: Props) {
  // 1. Data Merging Strategy: Create a unified timeline
  const dataMap = new Map<string, any>();

  const getOrCreateDay = (dateStr: string) => {
    if (!dataMap.has(dateStr)) {
      dataMap.set(dateStr, { date: dateStr, actual: null, predicted: null, rain: null });
    }
    return dataMap.get(dateStr);
  };

  // Process Groundwater History
  history.forEach(h => {
    const dateStr = h.timestamp.split('T')[0]; 
    const entry = getOrCreateDay(dateStr);
    entry.actual = h.water_level;
  });

  // Process Rainfall
  rainfall.forEach(r => {
    const dateStr = r.timestamp.split('T')[0];
    const entry = getOrCreateDay(dateStr);
    entry.rain = (entry.rain || 0) + r.amount_mm; 
  });

  // Process Forecasts
  forecasts.forEach(f => {
    const dateStr = f.forecast_date.split('T')[0];
    const entry = getOrCreateDay(dateStr);
    entry.predicted = f.predicted_level;
  });

  const data = Array.from(dataMap.values())
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  if (data.length === 0) {
    return (
      <div className="h-[450px] flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-lg bg-slate-50">
        <p className="text-slate-400 font-medium">No hydro-data available for this region</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-[500px]">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-bold text-slate-800">Hydro-Correlation Analysis</h3>
          <p className="text-sm text-slate-500">Groundwater Response to Rainfall Events</p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height="100%" minHeight={300}>
        <ComposedChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          
          <XAxis 
            dataKey="date" 
            tickFormatter={(str) => {
              const d = parseISO(str);
              return isValid(d) ? format(d, 'MMM d') : str;
            }}
            stroke="#94a3b8"
            fontSize={12}
            minTickGap={30}
          />

          {/* LEFT AXIS: Groundwater Depth (Line) */}
          <YAxis 
            yAxisId="left"
            label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 12 } }} 
            stroke="#64748b"
            fontSize={12}
            domain={['auto', 'auto']}
            reversed={true} 
          />

          {/* RIGHT AXIS: Rainfall (Bar) */}
          <YAxis 
            yAxisId="right"
            orientation="right"
            label={{ value: 'Rainfall (mm)', angle: 90, position: 'insideRight', style: { fill: '#06b6d4', fontSize: 12 } }} 
            stroke="#06b6d4"
            fontSize={12}
            domain={[0, 'auto']} 
          />

          <Tooltip
            labelFormatter={(label) => format(parseISO(label), 'PPP')}
            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
          />
          
          <Legend />

          <ReferenceLine yAxisId="left" y={criticalLevel} label="CRITICAL" stroke="#ef4444" strokeDasharray="3 3" />
          
          <Bar 
            yAxisId="right" 
            dataKey="rain" 
            name="Rainfall" 
            fill="#67e8f9" 
            opacity={0.4} 
            barSize={20}
            radius={[4, 4, 0, 0]}
          />
          <Line 
            yAxisId="left" 
            type="monotone" 
            dataKey="actual" 
            name="Groundwater Depth" 
            stroke="#3b82f6" 
            strokeWidth={3} 
            dot={false} 
            activeDot={{ r: 6 }}
          />
          <Line 
            yAxisId="left" 
            type="monotone" 
            dataKey="predicted" 
            name="AI Forecast" 
            stroke="#8b5cf6" 
            strokeWidth={3} 
            strokeDasharray="5 5" 
            dot={{ r: 4, strokeWidth: 2 }} 
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}