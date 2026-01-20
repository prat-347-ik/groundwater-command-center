"use client";

import { useEffect, useState } from 'react';
import { Activity, Database, AlertTriangle, CloudRain } from 'lucide-react';
import StatCard from '@/components/dashboard/StatCard';
import RegionGrid from '@/components/dashboard/RegionGrid';
import { opsClient } from '@/lib/api';

export default function Home() {
  // Initial state matches the shape of the 'counts' object
  const [stats, setStats] = useState({ regions: 0, wells: 0, readings: 0 });

  useEffect(() => {
    // Fetch system-wide counts from Service A
    opsClient.get('/stats/counts')
      .then(res => {
        // ✅ FIX: Access 'res.data.counts' instead of 'res.data'
        if (res.data.counts) {
          setStats(res.data.counts);
        }
      })
      .catch(err => console.error("Stats Error:", err));
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* 1. Header Section */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Command Center</h1>
          <p className="text-slate-500 mt-1">Groundwater Monitoring & Prediction System</p>
        </div>

        {/* 2. Vital Signs Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="Monitored Regions" 
            value={stats.regions} 
            icon={Activity} 
            color="blue"
          />
          <StatCard 
            title="Active Wells" 
            value={stats.wells} 
            icon={Database} 
            color="green" 
          />
          <StatCard 
            title="Total Data Points" 
            value={stats.readings?.toLocaleString() || 0} /* Added optional chaining just in case */
            icon={CloudRain} 
            color="amber"
          />
          <StatCard 
            title="Critical Alerts" 
            value="0" 
            icon={AlertTriangle} 
            color="red"
            trend="System Nominal" 
          />
        </div>

        {/* 3. Main Content: Region Grid */}
        <div>
          <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-600" />
            Live Monitoring Grid
          </h2>
          <RegionGrid />
        </div>

      </div>
    </main>
  );
}