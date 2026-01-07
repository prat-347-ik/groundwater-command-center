'use client';

import { useState, useRef } from 'react';
import { uploadRainfallCSV } from '@/lib/api';
import { UploadCloud, FileText, Check, AlertTriangle, Loader2 } from 'lucide-react';

export default function DataIngestion() {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (f: File) => {
    if (f.type !== 'text/csv' && !f.name.endsWith('.csv')) {
      alert('Please upload a valid CSV file.');
      return;
    }
    setFile(f);
    setResult(null); // Reset previous results
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadRainfallCSV(file);
      setResult({ success: true, count: res.details?.inserted || 0, total: res.details?.total || 0 });
      setFile(null);
    } catch (err: any) {
      setResult({ success: false, error: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
      <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <UploadCloud className="w-5 h-5 text-blue-500" />
        Climate Data Ingestion
      </h3>

      {!result ? (
        <div className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
              ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50'}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              className="hidden" 
              accept=".csv"
            />
            
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <FileText className="w-8 h-8 text-blue-500" />
                <span className="font-medium text-slate-700">{file.name}</span>
                <span className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-slate-400">
                <UploadCloud className="w-8 h-8" />
                <span className="text-sm">Drag & drop CSV or <span className="text-blue-500 font-medium">browse</span></span>
                <span className="text-xs opacity-70">Format: region_id, amount_mm, timestamp</span>
              </div>
            )}
          </div>

          {file && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex justify-center items-center gap-2"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Upload Data'}
            </button>
          )}
        </div>
      ) : (
        <div className={`p-4 rounded-lg border ${result.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-start gap-3">
            {result.success ? (
              <Check className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
            )}
            <div>
              <p className={`font-semibold ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                {result.success ? 'Upload Successful' : 'Upload Failed'}
              </p>
              {result.success ? (
                <p className="text-sm text-green-700 mt-1">
                  Processed {result.total} rows. Inserted {result.count} new records.
                </p>
              ) : (
                <p className="text-sm text-red-700 mt-1">{result.error}</p>
              )}
              
              <button 
                onClick={() => { setResult(null); setFile(null); }}
                className="mt-3 text-xs font-semibold uppercase tracking-wide underline opacity-80 hover:opacity-100"
              >
                Upload Another
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}