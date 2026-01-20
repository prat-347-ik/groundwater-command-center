"use client";

import { useEffect, useState } from 'react';
import { Search, Droplet, AlertTriangle } from 'lucide-react';
import { opsClient } from '@/lib/api';

interface Well {
  well_id: string;
  depth_m: number;
  status: 'Active' | 'Maintenance' | 'Decommissioned';
  last_reading_date?: string;
}

interface WellListProps {
  regionId: string;
}

export default function WellList({ regionId }: WellListProps) {
  const [wells, setWells] = useState<Well[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function fetchWells() {
      try {
        // Fetch wells filtered by this region
        const res = await opsClient.get(`/wells/regions/${regionId}/wells`);    
        const list = Array.isArray(res.data) ? res.data : (res.data.data || []);
        setWells(list);
      } catch (err) {
        console.error("Failed to load wells", err);
      } finally {
        setLoading(false);
      }
    }
    if (regionId) fetchWells();
  }, [regionId]);

  // Client-side search filtering
  const filteredWells = wells.filter(w => 
    w.well_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[600px]">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50">
        <h3 className="font-bold text-slate-700 flex items-center justify-between">
          Well Network
          <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded-full">{wells.length} Nodes</span>
        </h3>
        {/* Search Bar */}
        <div className="mt-3 relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Find well ID..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Scrollable List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {loading ? (
          <p className="text-center text-sm text-slate-400 mt-10">Scanning Network...</p>
        ) : filteredWells.length === 0 ? (
          <p className="text-center text-sm text-slate-400 mt-10">No wells found.</p>
        ) : (
          filteredWells.map((well) => (
            <div key={well.well_id} className="p-3 rounded-lg border border-slate-100 hover:border-blue-200 hover:bg-blue-50 transition-all cursor-pointer group">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium text-slate-800 text-sm">{well.well_id}</p>
                  <p className="text-xs text-slate-500 mt-1">Depth: {well.depth_m}m</p>
                </div>
                {well.status === 'Active' ? (
                  <Droplet className="h-4 w-4 text-emerald-500" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}