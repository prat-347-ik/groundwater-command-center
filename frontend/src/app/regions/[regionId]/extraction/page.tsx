"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getExtractionHistory, getWaterReadings, getRegionDetails } from '@/lib/api';
import ExtractionImpactChart from '@/components/extraction/ExtractionImpactChart';
import ExtractionForm from '@/components/extraction/ExtractionForm';
import ComplianceTracker from '@/components/extraction/ComplianceTracker';

export default function ExtractionPage() {
  const params = useParams();
  const regionId = params.regionId as string;

  const [logs, setLogs] = useState([]);
  const [readings, setReadings] = useState([]);
  const [region, setRegion] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [l, r, reg] = await Promise.all([
        getExtractionHistory(regionId),
        getWaterReadings(regionId),
        getRegionDetails(regionId)
      ]);
      setLogs(l);
      setReadings(r);
      setRegion(reg);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (regionId) fetchData();
  }, [regionId]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Operations Data...</div>;

  // Get latest water reading for compliance calculation
  const currentReading = readings.length > 0 ? readings[0] : null;

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Extraction Operations</h1>
        <p className="text-slate-500 text-sm">Monitor and control groundwater pumping for Region: <span className="font-mono">{regionId}</span></p>
      </header>

      {/* Top Row: Compliance & Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
           <ComplianceTracker region={region} currentLevel={currentReading?.water_level || 0} />
        </div>
        <div className="bg-blue-600 p-4 rounded-xl text-white shadow-md">
           <h4 className="text-blue-100 text-sm font-medium">Total Extraction (All Time)</h4>
           <div className="text-3xl font-bold mt-2">
             {(logs.reduce((acc, curr: any) => acc + curr.volume_liters, 0) / 1000).toLocaleString()} m³
           </div>
           <p className="text-xs text-blue-200 mt-1">{logs.length} logged events</p>
        </div>
      </div>

      {/* Middle Row: Main Chart */}
      <ExtractionImpactChart readings={readings} extractions={logs} />

      {/* Bottom Row: Form & Log Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form takes 1/3 width */}
        <div className="lg:col-span-1">
          <ExtractionForm regionId={regionId} onLogAdded={fetchData} />
        </div>

        {/* Recent Logs Table takes 2/3 width */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-100">
            <h3 className="font-bold text-slate-700">Recent Logs</h3>
          </div>
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="p-3">Date</th>
                  <th className="p-3">Type</th>
                  <th className="p-3 text-right">Volume (L)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log: any) => (
                  <tr key={log._id} className="hover:bg-slate-50">
                    <td className="p-3 text-slate-600">
                      {new Date(log.timestamp).toLocaleDateString()}
                      <span className="text-xs text-slate-400 block">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded-md text-xs font-medium uppercase tracking-wide">
                        {log.usage_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-3 text-right font-mono font-medium text-slate-700">
                      {log.volume_liters.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}