'use client';

import { useEffect, useState } from 'react';
import { fetchRegions, fetchHistoricalData, fetchForecasts, fetchRainfallData } from '@/lib/api';
import { Region, WaterReading, Forecast, RainfallReading } from '@/types';
import { AlertCircle, Loader2 } from 'lucide-react';

// Components
import RegionSelect from '@/components/dashboard/RegionSelect';
import HydroComboChart from '@/components/dashboard/HydroComboChart'; 
import PipelineStatus from '@/components/dashboard/PipelineStatus';
import PipelineControls from '@/components/dashboard/PipelineControls';
import DataIngestion from '@/components/dashboard/DataIngestion';
import KPIGrid from '@/components/dashboard/KPIGrid';
import SystemHealth from '@/components/dashboard/SystemHealth';

export default function DashboardPage() {
  // --- Global State ---
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  
  // --- Data State ---
  const [history, setHistory] = useState<WaterReading[]>([]);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [rainfall, setRainfall] = useState<RainfallReading[]>([]);
  
  // --- UX State ---
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // 1. Initial Boot: Load Regions
  useEffect(() => {
    async function init() {
      try {
        const res = await fetchRegions();
        if (res.data && res.data.length > 0) {
          setRegions(res.data);
          setSelectedRegionId(res.data[0].region_id);
        } else {
          setError("No regions found in the database.");
        }
      } catch (err) {
        console.error(err);
        setError("Failed to connect to Operations Service (A).");
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, []);

  // 2. Data Fetching: Runs on Region Change or Manual Refresh
  useEffect(() => {
    if (!selectedRegionId) return;

    async function loadData() {
      setIsLoading(true);
      setError(null);
      
      try {
        // Parallel Fetch for Speed
        const [histRes, fcRes, rainRes] = await Promise.all([
          fetchHistoricalData(selectedRegionId),
          fetchForecasts(selectedRegionId),
          fetchRainfallData(selectedRegionId)
        ]);

        setHistory(histRes.data || []);
        setForecasts(fcRes.data || []);
        setRainfall(rainRes.data || []);
      } catch (err) {
        console.error("Data Load Error:", err);
        setError("Failed to load analytics data. Services may be busy.");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [selectedRegionId, refreshTrigger]);

  const currentRegion = regions.find(r => r.region_id === selectedRegionId);

  return (
    // UPDATED: Changed background to bg-slate-100 for better contrast with white cards
    <main className="min-h-screen bg-slate-100 p-6 md:p-8 pb-16 relative text-slate-900 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* --- Header Section --- */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Groundwater Command Center</h1>
            <p className="text-slate-500 mt-1 flex items-center gap-2 font-medium">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-sm shadow-emerald-200" />
              Real-time Aquifer Monitoring System
            </p>
          </div>
          <PipelineStatus onSuccess={() => setRefreshTrigger(prev => prev + 1)} />
        </header>

        {/* --- Navigation & Context --- */}
        {/* UPDATED: Sharper border (border-slate-200) and distinct shadow */}
        <section className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 transition-all hover:shadow-md">
          <RegionSelect 
            regions={regions} 
            selectedId={selectedRegionId} 
            onSelect={setSelectedRegionId} 
          />
        </section>

        {/* --- Error Boundary UI --- */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-center gap-3 shadow-sm">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">{error}</span>
            <button 
              onClick={() => setRefreshTrigger(prev => prev + 1)}
              className="ml-auto text-sm font-semibold underline hover:text-red-900"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* --- Main Content Area --- */}
        {isLoading && !history.length ? (
          <DashboardSkeleton />
        ) : (
          <>
            {/* KPI Section */}
            <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <KPIGrid 
                history={history}
                forecasts={forecasts}
                rainfall={rainfall}
                criticalLevel={currentRegion?.critical_level || 0}
              />
            </section>

            {/* Analytics Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
              
              {/* Left: Charts */}
              <div className="lg:col-span-2 space-y-6">
                <HydroComboChart 
                  history={history} 
                  forecasts={forecasts}
                  rainfall={rainfall}
                  criticalLevel={currentRegion?.critical_level || 0} 
                />
              </div>

              {/* Right: Operations */}
              <div className="space-y-6">
                <PipelineControls />
                <DataIngestion />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Footer Status Bar */}
      <SystemHealth />
    </main>
  );
}

// --- Sub-Component: Loading Skeleton ---
function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* KPI Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-28 bg-slate-200 rounded-xl shadow-sm border border-slate-300/50"></div>
        ))}
      </div>
      {/* Main Grid Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 h-[500px] bg-slate-200 rounded-xl shadow-sm border border-slate-300/50"></div>
        <div className="space-y-6">
          <div className="h-[300px] bg-slate-200 rounded-xl shadow-sm border border-slate-300/50"></div>
          <div className="h-[200px] bg-slate-200 rounded-xl shadow-sm border border-slate-300/50"></div>
        </div>
      </div>
    </div>
  );
}