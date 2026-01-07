'use client';

import { useState } from 'react';
import { triggerPipeline, triggerJob } from '@/lib/api';
import { Loader2, Play, CheckCircle2, AlertCircle } from 'lucide-react'; // Ensure lucide-react is installed

export default function PipelineControls() {
  const [loading, setLoading] = useState<string | null>(null);
  const [status, setStatus] = useState<{ msg: string; type: 'success' | 'error' | 'neutral' }>({ 
    msg: 'Ready to run', 
    type: 'neutral' 
  });

  const handleRunJob = async (jobName: string, label: string) => {
    setLoading(jobName);
    setStatus({ msg: `Running ${label}...`, type: 'neutral' });
    
    try {
      // Maps to Service A -> Service B endpoints
      await triggerJob(jobName);
      setStatus({ msg: `✅ ${label} Completed`, type: 'success' });
    } catch (err: any) {
      setStatus({ msg: `❌ ${label} Failed: ${err.message}`, type: 'error' });
    } finally {
      setLoading(null);
    }
  };

  const handleFullPipeline = async () => {
    setLoading('full');
    setStatus({ msg: '🚀 Orchestrating Full Pipeline...', type: 'neutral' });
    
    try {
      await triggerPipeline();
      setStatus({ msg: '✅ Pipeline Triggered Successfully', type: 'success' });
    } catch (err: any) {
      setStatus({ msg: `❌ Pipeline Error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
      <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
        ML Operations Control
      </h3>

      {/* Status Bar */}
      <div className={`mb-6 p-3 rounded-lg text-sm font-medium flex items-center gap-2 
        ${status.type === 'success' ? 'bg-green-50 text-green-700' : 
          status.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-slate-50 text-slate-600'}`}>
        {status.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> :
         status.type === 'error' ? <AlertCircle className="w-4 h-4" /> :
         <Play className="w-4 h-4" />}
        {status.msg}
      </div>

      <div className="space-y-6">
        {/* Full Pipeline Button */}
        <button
          onClick={handleFullPipeline}
          disabled={!!loading}
          className="w-full py-3 px-4 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-300 
            text-white font-semibold rounded-lg shadow-md transition-all flex justify-center items-center gap-2"
        >
          {loading === 'full' ? <Loader2 className="w-5 h-5 animate-spin" /> : '🚀 Run End-to-End Pipeline'}
        </button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center">
            <span className="bg-white px-2 text-xs text-slate-400 uppercase tracking-wider">Or run steps individually</span>
          </div>
        </div>

        {/* Granular Controls Grid */}
        <div className="grid grid-cols-2 gap-3">
          <JobButton 
            label="1. ETL Ingest" 
            loading={loading === 'daily-summary'} 
            onClick={() => handleRunJob('daily-summary', 'ETL Process')} 
          />
          <JobButton 
            label="2. Train Model" 
            loading={loading === 'train'} 
            onClick={() => handleRunJob('train', 'Model Training')} 
          />
          <JobButton 
            label="3. Promote" 
            loading={loading === 'promote'} 
            onClick={() => handleRunJob('promote', 'Model Promotion')} 
          />
          <JobButton 
            label="4. Forecast" 
            loading={loading === 'forecast'} 
            onClick={() => handleRunJob('forecast', 'Inference')} 
          />
        </div>
      </div>
    </div>
  );
}

function JobButton({ label, loading, onClick }: { label: string, loading: boolean, onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="py-2 px-3 text-sm font-medium text-slate-600 bg-white border border-slate-200 
        hover:bg-slate-50 hover:border-slate-300 rounded-lg transition-all flex justify-center items-center gap-2"
    >
      {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : label}
    </button>
  );
}