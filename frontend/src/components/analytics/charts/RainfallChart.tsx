"use client";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { format } from 'date-fns';

export default function RainfallChart({ data }: { data: any[] }) {
  // Sort and take last 14 days
  const chartData = [...data]
    .sort((a, b) => new Date(a.timestamp || a.date).getTime() - new Date(b.timestamp || b.date).getTime())
    .slice(-14)
    .map((d: any) => ({
      date: format(new Date(d.timestamp || d.date), 'MMM dd'),
      amount: d.amount_mm
    }));

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm h-full flex flex-col">
      <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
        <span className="p-1.5 bg-sky-100 text-sky-600 rounded-md">🌧️</span>
        Recent Rainfall (14 Days)
      </h3>
      <div className="flex-1 min-h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} dy={5} />
            <YAxis tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} />
            <Tooltip 
              cursor={{fill: '#f8fafc'}}
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
            />
            <Bar dataKey="amount" fill="#38bdf8" radius={[4, 4, 0, 0]} barSize={20} name="Rainfall (mm)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}