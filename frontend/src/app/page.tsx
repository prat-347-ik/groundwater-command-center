import { Activity, Droplets, Map, AlertTriangle } from 'lucide-react';
import SimulationLab from '@/components/dashboard/SimulationLab';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Groundwater Command Center</h1>
        <p className="text-slate-600">Real-time Aquifer Monitoring & AI Forecasting</p>
      </header>

      {/* KPI Grid Placeholder (We'll wire this up next) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-slate-500 text-sm font-medium">Active Regions</h3>
            <Map className="text-blue-500 h-5 w-5" />
          </div>
          <p className="text-2xl font-bold text-slate-800">--</p>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-slate-500 text-sm font-medium">System Health</h3>
            <Activity className="text-green-500 h-5 w-5" />
          </div>
          <p className="text-2xl font-bold text-slate-800">Online</p>
        </div>
      </div>

      {/* Content Area - Simulation Lab Demo */}
      <div className="grid grid-cols-1 gap-8">
        <div className="h-[600px]"> 
          {/* Using the hardcoded Region ID from your backend tests.
              In the final version, this will be dynamic.
          */}
          <SimulationLab 
            regionId="65f4fc28-a5f9-47e0-b326-962b20bb35b1" 
            regionName="Nagpur Zone 1" 
            criticalLevel={10.0} 
          />
        </div>
      </div>
    </main>
  );
}