"use client";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { format } from 'date-fns';

export default function ExtractionChart({ data }: { data: any[] }) {
  // Aggregate by date (in case multiple pumps run on same day)
  const aggregated = data.reduce((acc: any, curr: any) => {
    const date = format(new Date(curr.timestamp), 'yyyy-MM-dd');
    acc[date] = (acc[date] || 0) + curr.volume_liters;
    return acc;
  }, {});

  const chartData = Object.entries(aggregated)
    .sort((a: any, b: any) => new Date(a[0]).getTime() - new Date(b[0]).getTime()) // Sort by date
    .slice(-14) // Last 14 days
    .map(([date, vol]) => ({
      date: format(new Date(date), 'MMM dd'),
      volume: (vol as number) / 1000 // Convert to kL
    }));

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm h-full flex flex-col">
       <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
        <span className="p-1.5 bg-amber-100 text-amber-600 rounded-md">⚙️</span>
        Extraction (Last 14 Days)
      </h3>
      <div className="flex-1 min-h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} dy={5} />
            <YAxis tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} />
            <Tooltip 
              cursor={{fill: '#fffbeb'}} 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
            />
            <Bar dataKey="volume" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={20} name="Volume (kL)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}