'use client';

import { useEffect, useState } from 'react';
import { Activity, Server, Database, CloudRain } from 'lucide-react';

export default function SystemHealth() {
  const [isOnline, setIsOnline] = useState(true);

  // Simple ping to Gateway (Service A)
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_SERVICE_A_URL || 'http://localhost:4000/api/v1'}/regions`, { method: 'HEAD' });
        setIsOnline(res.ok);
      } catch {
        setIsOnline(false);
      }
    };
    
    // Check every 30 seconds
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 px-6 py-2 flex justify-between items-center text-xs text-slate-500 z-50">
      <div className="flex gap-6">
        
        {/* Service A Indicator */}
        <div className="flex items-center gap-2">
          <Server className="w-3 h-3" />
          <span className="font-semibold">OPS Gateway (A):</span>
          <span className={`flex items-center gap-1.5 ${isOnline ? 'text-emerald-600' : 'text-red-500'}`}>
            <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`} />
            {isOnline ? 'Online' : 'Unreachable'}
          </span>
        </div>

        {/* Service B Indicator (Simulated via Gateway) */}
        <div className="hidden sm:flex items-center gap-2">
          <Activity className="w-3 h-3" />
          <span className="font-semibold">Analytics Engine (B):</span>
          <span className="text-emerald-600 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Standby
          </span>
        </div>

        {/* Service C Indicator */}
        <div className="hidden sm:flex items-center gap-2">
          <CloudRain className="w-3 h-3" />
          <span className="font-semibold">Climate Service (C):</span>
          <span className="text-emerald-600 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Active
          </span>
        </div>

      </div>
      
      <div className="flex items-center gap-2 opacity-50">
        <Database className="w-3 h-3" />
        <span>v2.4.0 (Distributed)</span>
      </div>
    </div>
  );
}