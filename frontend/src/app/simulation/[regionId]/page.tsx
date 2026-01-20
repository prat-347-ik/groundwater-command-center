"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Droplets, MapPin, AlertCircle } from 'lucide-react';
import { opsClient, analyticsClient } from '@/lib/api';
import UnifiedChart from '@/components/analytics/UnifiedChart';
import WellList from '@/components/analytics/WellList'; // 👈 Import new component

export default function RegionAnalyticsPage() {
  const params = useParams();
  // Support both folder naming conventions ([id] or [regionId])
  const regionId = (params.id || params.regionId) as string;

  const [region, setRegion] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any[]>([]);
  const [rainfall, setRainfall] = useState<any[]>([]); // 👈 New State
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDeepDive() {
      try {
        console.log(`📡 Fetching intelligence for Region: ${regionId}`);

        // 4 Parallel Requests (Now including Rainfall)
        const [regionRes, historyRes, forecastRes, rainRes] = await Promise.all([
          opsClient.get(`/regions/${regionId}`),
          opsClient.get(`/water-readings?region_id=${regionId}&limit=30`),
          analyticsClient.get(`/forecasts/${regionId}`),
          opsClient.get(`/rainfall?region_id=${regionId}&limit=30`) // 👈 Fetch Rainfall
        ]);

        setRegion(regionRes.data.data || regionRes.data);
        setHistory(historyRes.data.data || []);
        setForecast(forecastRes.data || []);
        setRainfall(rainRes.data.data || []); // 👈 Set Rainfall

      } catch (err) {
        console.error("Failed to load region analytics", err);
      } finally {
        setLoading(false);
      }
    }

    if (regionId) fetchDeepDive();
  }, [regionId]);

  if (loading) return <div className="p-10 text-center">Loading Intelligence Data...</div>;
  if (!region) return <div className="p-10 text-center text-red-500">Region Not Found</div>;

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors">
              <ArrowLeft className="h-5 w-5 text-slate-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                {region.name}
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full border border-blue-200">
                  {region.soil_type || 'Unknown Soil'}
                </span>
              </h1>
              <div className="flex items-center gap-4 text-sm text-slate-500 mt-1">
                <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {region.district}, {region.state}</span>
                <span className="flex items-center gap-1"><AlertCircle className="h-4 w-4" /> Limit: {region.critical_level || region.critical_water_level_m}m</span>
              </div>
            </div>
          </div>

          <Link 
            href={`/simulation/${regionId}`}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium shadow-sm transition-all"
          >
            <Droplets className="h-4 w-4" /> Open Simulation Lab
          </Link>
        </div>

        {/* Main Analytics Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Chart */}
          <div className="lg:col-span-2 space-y-6">
            <UnifiedChart 
              history={history} 
              forecast={forecast}
              rainfall={rainfall} // 👈 Pass Rainfall
              criticalLevel={region.critical_level || region.critical_water_level_m} 
            />
          </div>

          {/* Right Column: Well List */}
          <div className="space-y-6">
            <WellList regionId={regionId} /> {/* 👈 Render Real Component */}
          </div>

        </div>
      </div>
    </main>
  );
}