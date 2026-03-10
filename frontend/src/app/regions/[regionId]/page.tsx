"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Droplets, MapPin, AlertCircle, TrendingDown } from 'lucide-react';
import { opsClient, analyticsClient } from '@/lib/api';

// 🆕 Import the new separated charts
import WaterLevelChart from '@/components/analytics/charts/WaterLevelChart';
import RainfallChart from '@/components/analytics/charts/RainfallChart';
import ExtractionChart from '@/components/analytics/charts/ExtractionChart';
import WellList from '@/components/analytics/WellList';

export default function RegionAnalyticsPage() {
  const params = useParams();
  const regionId = (params.id || params.regionId) as string;

  const [region, setRegion] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any[]>([]);
  const [rainfall, setRainfall] = useState<any[]>([]);
  const [extraction, setExtraction] = useState<any[]>([]); // 🆕 State for extraction
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDeepDive() {
      try {
        if (!regionId) return;

        // 🆕 Added extraction fetch to the Promise.all
        const [regionRes, historyRes, forecastRes, rainRes, extractRes] = await Promise.all([
          opsClient.get(`/regions/${regionId}`),
          opsClient.get(`/water-readings?region_id=${regionId}&limit=30`),
          analyticsClient.get(`/forecasts/${regionId}`),
          opsClient.get(`/rainfall?region_id=${regionId}&limit=30`),
          opsClient.get(`/extraction/region/${regionId}`) // Matches Service A route
        ]);

        setRegion(regionRes.data.data || regionRes.data);
        setHistory(historyRes.data.data || []);
        setForecast(forecastRes.data || []);
        setRainfall(rainRes.data.data || []);
        setExtraction(extractRes.data.data || []);

      } catch (err) {
        console.error("Failed to load region analytics", err);
      } finally {
        setLoading(false);
      }
    }

    fetchDeepDive();
  }, [regionId]);

  if (loading) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-500 font-medium animate-pulse">Loading Command Center...</p>
      </div>
    </div>
  );

  if (!region) return <div className="p-10 text-center text-red-500">Region Not Found</div>;

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2.5 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm">
              <ArrowLeft className="h-5 w-5 text-slate-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                {region.name}
                <span className={`text-xs px-2.5 py-1 rounded-full border font-medium
                  ${region.status === 'Critical' 
                    ? 'bg-red-50 text-red-700 border-red-200' 
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                  {region.status || 'Active'}
                </span>
              </h1>
              <div className="flex items-center gap-4 text-sm text-slate-500 mt-1.5">
                <span className="flex items-center gap-1.5"><MapPin className="h-4 w-4" /> {region.district}, {region.state}</span>
                <span className="flex items-center gap-1.5"><TrendingDown className="h-4 w-4" /> Limit: {region.critical_level || region.critical_water_level_m}m</span>
              </div>
            </div>
          </div>

          <Link 
            href={`/simulation/${regionId}`}
            className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium shadow-sm hover:shadow-md transition-all active:scale-95"
          >
            <Droplets className="h-4 w-4" /> 
            Open Simulation Lab
          </Link>
        </div>

        {/* 🆕 The Dashboard Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Main Visualizations Column (Spans 8 cols) */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* 1. Primary Chart: Water Level */}
            <WaterLevelChart 
              history={history} 
              forecast={forecast}
              criticalLevel={region.critical_level || region.critical_water_level_m} 
            />

            {/* 2. Secondary Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-64">
              <RainfallChart data={rainfall} />
              <ExtractionChart data={extraction} />
            </div>
          </div>

          {/* Sidebar Column: Well List (Spans 4 cols) */}
          <div className="lg:col-span-4 flex flex-col h-full">
             <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex-1 overflow-hidden">
                <WellList regionId={regionId} />
             </div>
          </div>

        </div>
      </div>
    </main>
  );
}