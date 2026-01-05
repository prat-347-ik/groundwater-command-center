'use client';

import { useEffect, useState } from 'react';
import { fetchRegions, fetchHistoricalData, fetchForecasts } from '@/lib/api';
import { Region, WaterReading, Forecast } from '@/types';
import RegionSelect from '@/components/dashboard/RegionSelect';
import MainChart from '@/components/dashboard/MainChart';
import PipelineStatus from '@/components/dashboard/PipelineStatus';

export default function DashboardPage() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  
  const [history, setHistory] = useState<WaterReading[]>([]);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  
  // 1. Load Regions on Mount
  useEffect(() => {
    fetchRegions().then((res) => {
      if (res.success && res.data.length > 0) {
        setRegions(res.data);
        setSelectedRegionId(res.data[0].region_id);
      }
    }).catch(err => console.error("Failed to load regions:", err));
  }, []);

  // 2. Load Data when Region Changes
  useEffect(() => {
    if (!selectedRegionId) return;

    // Parallel data fetching
    Promise.all([
      fetchHistoricalData(selectedRegionId),
      fetchForecasts(selectedRegionId)
    ]).then(([histRes, fcRes]) => {
      setHistory(histRes.data || []);
      setForecasts(fcRes.data || []);
    }).catch(err => console.error("Failed to load dashboard data:", err));
  }, [selectedRegionId]);

  const currentRegion = regions.find(r => r.region_id === selectedRegionId);

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Groundwater Command Center</h1>
            <p className="text-slate-500 mt-1">Real-time aquifer monitoring & predictive analytics</p>
          </div>
          <PipelineStatus />
        </header>

        {/* Controls Section */}
        <section className="bg-white p-4 rounded-lg shadow-sm border border-slate-100 flex flex-col sm:flex-row gap-6 items-start sm:items-center">
          <RegionSelect 
            regions={regions} 
            selectedId={selectedRegionId} 
            onSelect={setSelectedRegionId} 
          />
          
          {/* Quick Stats (Optional) */}
          {currentRegion && (
             <div className="flex gap-6 text-sm">
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold">Coordinates</span>
                 <span className="font-mono text-slate-700">
                   {/*{currentRegion.coordinates.lat.toFixed(2)}, {currentRegion.coordinates.lng.toFixed(2)} */}
                 </span>
               </div>
               <div>
                 <span className="block text-slate-500 text-xs uppercase font-semibold">Critical Level</span>
                 <span className="font-mono text-red-600 font-bold">{currentRegion.critical_level}m</span>
               </div>
             </div>
          )}
        </section>

        {/* Visualization Section */}
        <section>
          <MainChart 
            history={history} 
            forecasts={forecasts} 
            criticalLevel={currentRegion?.critical_level || 0} 
          />
        </section>

      </div>
    </main>
  );
}