'use client';

import { useState } from 'react';
import { triggerPipeline } from '@/lib/api';
import { Loader2, Zap } from 'lucide-react';

export default function PipelineStatus() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await triggerPipeline();
      setMessage(`✅ ${res.message}`);
      // Clear success message after 5 seconds
      setTimeout(() => setMessage(null), 5000);
    } catch (err: any) {
      setMessage(`❌ ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        onClick={handleRun}
        disabled={loading}
        className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
        Run Forecast Model
      </button>
      {message && <span className="text-xs font-medium text-slate-600">{message}</span>}
    </div>
  );
}