"use client";

import { useState } from 'react';
import { createExtractionLog } from '@/lib/api';

export default function ExtractionForm({ regionId, onLogAdded }: { regionId: string, onLogAdded: () => void }) {
  const [volume, setVolume] = useState('');
  const [type, setType] = useState('irrigation');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');
    setErrorMsg('');

    try {
      await createExtractionLog({
        region_id: regionId,
        volume_liters: Number(volume),
        usage_type: type
      });
      setStatus('success');
      setVolume('');
      onLogAdded(); // Refresh parent data
      setTimeout(() => setStatus('idle'), 3000);
    } catch (err: any) {
      setStatus('error');
      // Handle the specific "Unsafe Yield" error from backend
      if (err.response?.status === 409) {
        setErrorMsg("⚠️ Compliance Block: " + err.response.data.error);
      } else {
        setErrorMsg("Failed to log extraction.");
      }
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="font-bold text-slate-800 mb-4">Log New Extraction</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Volume (Liters)</label>
          <input 
            type="number" 
            required
            min="0"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="e.g. 5000"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Usage Type</label>
          <select 
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full p-2 border border-slate-300 rounded-lg outline-none"
          >
            <option value="irrigation">Irrigation</option>
            <option value="industrial">Industrial</option>
            <option value="domestic">Domestic</option>
            <option value="industrial_cooling">Industrial Cooling</option>
          </select>
        </div>

        <button 
          type="submit" 
          disabled={status === 'loading'}
          className={`w-full py-2 rounded-lg font-medium transition-colors ${
            status === 'loading' ? 'bg-slate-100 text-slate-400' : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {status === 'loading' ? 'Verifying Compliance...' : 'Submit Log'}
        </button>

        {status === 'success' && <p className="text-sm text-green-600 text-center">✅ Logged successfully</p>}
        {status === 'error' && <p className="text-sm text-red-600 text-center mt-2">{errorMsg}</p>}
      </form>
    </div>
  );
}