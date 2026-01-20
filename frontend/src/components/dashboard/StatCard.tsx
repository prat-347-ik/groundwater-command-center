import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  color?: "blue" | "red" | "green" | "amber";
}

export default function StatCard({ title, value, icon: Icon, trend, color = "blue" }: StatCardProps) {
  const colorMap = {
    blue: "bg-blue-50 text-blue-600",
    red: "bg-red-50 text-red-600",
    green: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600"
  };

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900">{value}</h3>
        {trend && <p className="text-xs text-slate-400 mt-2">{trend}</p>}
      </div>
      <div className={`p-3 rounded-lg ${colorMap[color]}`}>
        <Icon className="h-6 w-6" />
      </div>
    </div>
  );
}