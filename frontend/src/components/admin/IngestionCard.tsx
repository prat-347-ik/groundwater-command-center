"use client";

import { useState } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, FileUp } from 'lucide-react';
import { opsClient, climateClient } from '@/lib/api';

interface IngestionCardProps {
  title: string;
  description: string;
  service: 'ops' | 'climate';
  endpoint: string;
  acceptedFile?: string;
}

export default function IngestionCard({ title, description, service, endpoint, acceptedFile = ".csv" }: IngestionCardProps) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setMessage('');

    const formData = new FormData();
    formData.append('file', file);

    const client = service === 'ops' ? opsClient : climateClient;

    try {
      // Axios automatically sets 'Content-Type': 'multipart/form-data' when sending FormData
      const res = await client.post(endpoint, formData);
      setStatus('success');
      setMessage(res.data.message || 'Ingestion started successfully');
      setFile(null); // Reset
    } catch (err: any) {
      console.error("Upload Error", err);
      setStatus('error');
      setMessage(err.response?.data?.message || err.message || "Upload Failed");
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-start gap-4 mb-4">
        <div className={`p-3 rounded-lg ${service === 'ops' ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'}`}>
          <UploadCloud className="h-6 w-6" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* File Input */}
        <div className="relative border-2 border-dashed border-slate-200 rounded-lg p-6 hover:bg-slate-50 transition-colors text-center cursor-pointer">
          <input 
            type="file" 
            accept={acceptedFile}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          {file ? (
            <div className="flex items-center justify-center gap-2 text-blue-600 font-medium">
              <FileUp className="h-4 w-4" />
              {file.name}
            </div>
          ) : (
            <span className="text-sm text-slate-400">Drop CSV here or click to browse</span>
          )}
        </div>

        {/* Action Button */}
        <button
          onClick={handleUpload}
          disabled={!file || status === 'uploading'}
          className="w-full py-2 px-4 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium flex justify-center items-center gap-2"
        >
          {status === 'uploading' ? 'Uploading Stream...' : 'Start Ingestion'}
        </button>

        {/* Feedback Message */}
        {status === 'success' && (
          <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 p-2 rounded">
            <CheckCircle className="h-4 w-4" /> {message}
          </div>
        )}
        {status === 'error' && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-2 rounded">
            <AlertTriangle className="h-4 w-4" /> {message}
          </div>
        )}
      </div>
    </div>
  );
}