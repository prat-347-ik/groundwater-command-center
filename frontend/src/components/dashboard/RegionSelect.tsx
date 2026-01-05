'use client';

import { Region } from '@/types';

interface Props {
  regions: Region[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function RegionSelect({ regions, selectedId, onSelect }: Props) {
  return (
    <div className="w-full max-w-xs">
      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
        Monitoring Region
      </label>
      <select
        value={selectedId}
        onChange={(e) => onSelect(e.target.value)}
        className="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 py-2 px-3 bg-white border text-slate-700"
      >
        {regions.length === 0 && <option>Loading regions...</option>}
        {regions.map((region) => (
          <option key={region.region_id} value={region.region_id}>
            {region.name} ({region.state})
          </option>
        ))}
      </select>
    </div>
  );
}