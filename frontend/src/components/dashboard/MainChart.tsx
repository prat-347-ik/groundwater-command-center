'use client';

import { 
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine 
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { WaterReading, Forecast } from '@/types';

interface Props {
  history: WaterReading[];
  forecasts: Forecast[];
  criticalLevel: number;
}

export default function MainChart({ history, forecasts, criticalLevel }: Props) {
  // Combine data for the chart
  const data = [
    ...history.map(h => ({
      date: h.timestamp,
      actual: h.water_level,
      predicted: null,
    })),
    ...forecasts.map(f => ({
      date: f.forecast_date,
      actual: null,
      predicted: f.predicted_level,
    }))
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  if (data.length === 0) {
    return (
      <div className="h-[400px] flex items-center justify-center border-2 border-dashed border-slate-200 rounded-lg">
        <p className="text-slate-400">No data available for this region</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-[450px]">
      <h3 className="text-lg font-bold text-slate-800 mb-4">Groundwater Depth & Forecast</h3>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis 
            dataKey="date" 
            tickFormatter={(str) => format(parseISO(str), 'MMM d')}
            stroke="#64748b"
            fontSize={12}
            minTickGap={30}
          />
          <YAxis 
            label={{ value: 'Depth (Meters)', angle: -90, position: 'insideLeft', style: { fill: '#64748b' } }} 
            stroke="#64748b"
            fontSize={12}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelFormatter={(label) => format(parseISO(label), 'PPP')}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          
          <ReferenceLine y={criticalLevel} label="CRITICAL THRESHOLD" stroke="#ef4444" strokeDasharray="3 3" />
          
          <Line 
            type="monotone" 
            dataKey="actual" 
            name="Historical Data" 
            stroke="#0ea5e9" 
            strokeWidth={2} 
            dot={false} 
            activeDot={{ r: 6 }}
          />
          <Line 
            type="monotone" 
            dataKey="predicted" 
            name="AI Forecast (7-Day)" 
            stroke="#8b5cf6" 
            strokeWidth={2} 
            strokeDasharray="5 5" 
            dot={{ r: 4, strokeWidth: 2 }} 
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}