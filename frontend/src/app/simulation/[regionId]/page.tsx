"use client";

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import SimulationLab from '@/components/dashboard/SimulationLab';

export default function SimulationPage() {
  const params = useParams();
  const regionId = (params.id || params.regionId) as string;

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Breadcrumb / Navigation */}
        <div className="flex items-center gap-4 mb-6">
           {/* Back button goes to the Dashboard, not Home */}
           <Link href={`/regions/${regionId}`} className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors">
              <ArrowLeft className="h-5 w-5 text-slate-600" />
            </Link>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Link href="/" className="hover:text-blue-600">Home</Link>
            <span>/</span>
            <Link href={`/regions/${regionId}`} className="hover:text-blue-600">Region Dashboard</Link>
            <span>/</span>
            <span className="font-semibold text-slate-900">Simulation Lab</span>
          </div>
        </div>

        {/* The Interactive Tool */}
        <div className="h-[600px]">
          <SimulationLab 
            regionId={regionId}
            regionName="Interactive Model"
            criticalLevel={15.0} // You can fetch this if you want, but static is fine for the lab
          />
        </div>
        
      </div>
    </main>
  );
}