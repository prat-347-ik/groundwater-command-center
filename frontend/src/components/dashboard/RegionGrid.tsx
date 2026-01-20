"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MapPin, ArrowRight, Activity } from 'lucide-react';
import { opsClient } from '@/lib/api';

interface Region {
  _id: string;        // MongoDB Internal ID (Ignore for routing)
  region_id: string;  // 👈 IMPORTANT: The UUID used by Service B
  name: string;
  state: string;
  district: string;
  soil_type: string;
  critical_level?: number; // Check if your API returns 'critical_level' or 'critical_water_level_m'
}

export default function RegionGrid() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRegions() {
      try {
        const res = await opsClient.get('/regions');
        // Handle wrapped data structure if present
        const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
        setRegions(list);
      } catch (err) {
        console.error("Failed to load regions", err);
      } finally {
        setLoading(false);
      }
    }
    fetchRegions();
  }, []);

  if (loading) return <div className="p-10 text-center text-slate-400">Loading Intelligence Network...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {regions.map((region) => (
        <Link 
          key={region._id} 
          // 🛑 WAS: href={`/simulation/${region._id}`}
          // ✅ FIX: Use the UUID 'region_id'
          href={`/simulation/${region.region_id}`}
          className="group relative block bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all p-6"
        >
          <div className="flex justify-between items-start mb-4">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors">
              <MapPin className="h-6 w-6" />
            </div>
            <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-semibold rounded-md border border-slate-200">
              {/* Ensure this property matches your API response */}
              Limit: {region.critical_level ?? 'N/A'}m
            </span>
          </div>
          
          <h3 className="text-lg font-bold text-slate-900 mb-1">{region.name}</h3>
          <p className="text-sm text-slate-500 mb-4">{region.district}, {region.state}</p>
          
          <div className="flex items-center gap-4 text-xs text-slate-500 border-t border-slate-100 pt-4">
            <div className="flex items-center gap-1">
              <Activity className="h-3 w-3 text-emerald-500" />
              <span>Monitoring Active</span>
            </div>
            <div className="ml-auto flex items-center gap-1 text-blue-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
              Open Lab <ArrowRight className="h-3 w-3" />
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}