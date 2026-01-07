import { Region, WaterReading, RainfallReading, Forecast, ApiResponse, JobResponse } from '@/types';

// Gateway URL (Service A)
const SERVICE_A_URL = process.env.NEXT_PUBLIC_SERVICE_A_URL || 'http://localhost:4000/api/v1';

// --- Data Retrieval ---

export async function fetchRegions(): Promise<ApiResponse<Region[]>> {
  const res = await fetch(`${SERVICE_A_URL}/regions`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch regions');
  return res.json();
}

export async function fetchHistoricalData(regionId: string): Promise<ApiResponse<WaterReading[]>> {
  const res = await fetch(`${SERVICE_A_URL}/water-readings?region_id=${regionId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch water readings');
  return res.json();
}

// [NEW] Fetch Rainfall History (Proxies to Service C)
export async function fetchRainfallData(regionId: string): Promise<ApiResponse<RainfallReading[]>> {
  const res = await fetch(`${SERVICE_A_URL}/rainfall?region_id=${regionId}&limit=365`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch rainfall data');
  return res.json();
}

export async function fetchForecasts(regionId: string): Promise<ApiResponse<Forecast[]>> {
  const res = await fetch(`${SERVICE_A_URL}/forecasts/${regionId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch forecasts');
  return res.json();
}

// --- Control Plane (Proxies to Service B & C) ---

// [UPDATED] Trigger Full Pipeline
export async function triggerPipeline(date?: string): Promise<JobResponse> {
  const payload = date ? { date } : {};
  const res = await fetch(`${SERVICE_A_URL}/pipeline/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Pipeline trigger failed');
  return res.json();
}

// [NEW] Trigger Granular Job (Train, Promote, Forecast)
export async function triggerJob(jobName: string): Promise<JobResponse> {
  const res = await fetch(`${SERVICE_A_URL}/jobs/${jobName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to trigger job: ${jobName}`);
  return res.json();
}

// [NEW] Upload CSV to Ingestion Engine (Service C)
export async function uploadRainfallCSV(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${SERVICE_A_URL}/rainfall/ingest/csv`, {
    method: 'POST',
    body: formData, // Content-Type is set automatically by fetch for FormData
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'CSV Upload Failed');
  }
  return res.json();
}

// [NEW] Check System Health (Service A)
export async function checkSystemHealth(): Promise<any> {
   try {
     const res = await fetch('http://localhost:4000/health');
     return res.ok ? 'UP' : 'DOWN';
   } catch {
     return 'DOWN';
   }
}