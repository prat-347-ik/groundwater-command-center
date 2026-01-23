"use client";

interface Props {
  region: any;
  currentLevel: number; // Most recent water depth reading
}

export default function ComplianceTracker({ region, currentLevel }: Props) {
  if (!region || !currentLevel) return null;

  // 1. Calculate Available "Buffer" (Distance to Critical Level)
  const bufferDepthM = region.critical_water_level_m - currentLevel; 
  
  // 2. Calculate Volume of water in that buffer (Safe Yield Volume)
  // Formula: Volume = Area * Depth * Specific Yield
  const area = region.aquifer_area_m2 || 1000000; // Default fallback
  const sy = region.specific_yield || 0.15;
  
  const safeYieldVolM3 = bufferDepthM * area * sy;
  const isCritical = bufferDepthM <= 0;

  return (
    <div className={`p-4 rounded-xl border shadow-sm ${isCritical ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200'}`}>
      <div className="flex justify-between items-start">
        <div>
          <h4 className={`text-sm font-bold uppercase ${isCritical ? 'text-red-700' : 'text-emerald-700'}`}>
            {isCritical ? '🚫 Extraction Halt' : '✅ Safe to Extract'}
          </h4>
          <p className="text-xs text-slate-600 mt-1">
            Current Depth: <span className="font-mono font-bold">{currentLevel.toFixed(2)}m</span>
          </p>
          <p className="text-xs text-slate-600">
             Critical Limit: <span className="font-mono font-bold">{region.critical_water_level_m}m</span>
          </p>
        </div>
        <div className="text-right">
          <span className="block text-2xl font-bold text-slate-800">
            {isCritical ? 0 : Math.floor(safeYieldVolM3).toLocaleString()} m³
          </span>
          <span className="text-xs text-slate-500">Remaining Safe Yield</span>
        </div>
      </div>
      
      {/* Progress Bar Visualizing the Buffer */}
      <div className="w-full bg-white h-2 rounded-full mt-3 overflow-hidden border border-slate-100">
        <div 
          className={`h-full ${isCritical ? 'bg-red-500' : 'bg-emerald-500'}`} 
          // Simple visual approximation: assume 10m buffer is "full"
          style={{ width: `${Math.min(Math.max((bufferDepthM / 5) * 100, 0), 100)}%` }} 
        />
      </div>
    </div>
  );
}