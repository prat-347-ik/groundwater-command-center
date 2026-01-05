'use client';

import { useState } from 'react';
import { triggerPipeline } from '@/lib/api';
import { Loader2, Zap, CheckCircle2 } from 'lucide-react';

// ✅ Fix: Define the interface for the props
interface PipelineStatusProps {
  onSuccess: () => void;
}

export default function PipelineStatus({ onSuccess }: PipelineStatusProps) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setStatus('idle');
    setMessage(null);
    
    try {
      const res = await triggerPipeline();
      setStatus('success');
      setMessage(res.message || "Pipeline finished successfully");
      
      // ✅ Fix: Call the onSuccess callback to tell the parent to refresh
      onSuccess(); 

      // Reset success message after 5 seconds
      setTimeout(() => {
        setStatus('idle');
        setMessage(null);
      }, 5000);
      
    } catch (err: any) {
      setStatus('error');
      setMessage(err.message || "Pipeline failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-center gap-3">
        {/* Status Message Area */}
        {status === 'success' && (
          <span className="text-xs font-medium text-green-600 flex items-center gap-1 animate-in fade-in slide-in-from-bottom-1">
            <CheckCircle2 className="w-3 h-3" />
            {message}
          </span>
        )}
        {status === 'error' && (
          <span className="text-xs font-medium text-red-600 animate-in fade-in">
            {message}
          </span>
        )}

        {/* Action Button */}
        <button
          onClick={handleRun}
          disabled={loading}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
            ${loading 
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow'
            }
          `}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Running Model...</span>
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              <span>Run Forecast</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}