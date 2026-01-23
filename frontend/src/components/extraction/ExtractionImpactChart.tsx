"use client";

import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { format } from 'date-fns';

interface Props {
  readings: any[];
  extractions: any[];
}

export default function ExtractionImpactChart({ readings, extractions }: Props) {
  // 1. Merge Data by Date
  const dataMap = new Map();

  // Helper to init date entry
  const getEntry = (dateStr: string) => {
    const key = dateStr.split('T')[0];
    if (!dataMap.has(key)) {
      dataMap.set(key, { 
        date: key, 
        displayDate: format(new Date(key), 'MMM dd'),
        level: null, 
        extraction: 0 
      });
    }
    return dataMap.get(key);
  };

  readings.forEach(r => {
    const entry = getEntry(r.timestamp);
    entry.level = r.water_level;
  });

  extractions.forEach(e => {
    const entry = getEntry(e.timestamp);
    // Convert Liters to Cubic Meters (m³) for better scaling
    entry.extraction += (e.volume_liters / 1000); 
  });

  const combinedData = Array.from(dataMap.values()).sort((a, b) => 
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  return (
    <div className="h-[400px] w-full bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="text-sm font-bold text-slate-700 mb-4">Extraction vs. Groundwater Level</h3>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={combinedData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="displayDate" tick={{fontSize: 12}} />
          
          {/* Left Axis: Water Level (Reversed because deeper is higher number) */}
          <YAxis 
            yAxisId="left"
            label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft' }} 
            domain={['auto', 'auto']}
            reversed={true} 
          />
          
          {/* Right Axis: Extraction Volume */}
          <YAxis 
            yAxisId="right"
            orientation="right"
            label={{ value: 'Extraction (m³)', angle: 90, position: 'insideRight' }} 
          />

          <Tooltip 
             formatter={(value: number, name: string) => [
               value.toFixed(2), 
               name === 'extraction' ? 'Volume (m³)' : 'Depth (m)'
             ]}
          />
          <Legend />

          <Bar 
            yAxisId="right"
            dataKey="extraction" 
            name="Extraction (m³)" 
            fill="#f59e0b" 
            opacity={0.6}
            barSize={20}
          />
          
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="level" 
            name="Water Depth" 
            stroke="#2563eb" 
            strokeWidth={3} 
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}