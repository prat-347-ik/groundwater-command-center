"use client";

import { ShieldCheck, ServerCog } from 'lucide-react';
import IngestionCard from '@/components/admin/IngestionCard';

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-3 bg-slate-900 text-white rounded-xl">
            <ShieldCheck className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Data Operations Center</h1>
            <p className="text-slate-500">Manage data ingestion pipelines and system overrides.</p>
          </div>
        </div>

        {/* Ingestion Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* 1. Groundwater Readings */}
          <IngestionCard 
            title="Bulk Water Readings"
            description="Upload sensor data (CSV). Requires columns: well_id, water_level, timestamp."
            service="ops"
            endpoint="/water-readings/ingest/csv"
          />

          {/* 2. Weather Data */}
          <IngestionCard 
            title="Historical Weather Data"
            description="Upload rainfall/humidity logs. Service C will index this for correlations."
            service="climate"
            endpoint="/weather/ingest/csv"
          />
          
        </div>

        {/* System Status (Placeholder for future) */}
        <div className="bg-slate-100 rounded-xl p-6 border border-slate-200 flex items-center justify-between opacity-75">
          <div className="flex items-center gap-3">
            <ServerCog className="h-6 w-6 text-slate-500" />
            <span className="font-medium text-slate-600">Automated Pipeline Status</span>
          </div>
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded font-bold">ALL SYSTEMS NOMINAL</span>
        </div>

      </div>
    </main>
  );
}