import { Region, WaterReading, Forecast, ApiResponse } from '@/types';

// Service A acts as the Gateway for all requests
const SERVICE_A_URL = process.env.NEXT_PUBLIC_SERVICE_A_URL || 'http://localhost:8000/api/v1';

// --- Service A: Data Retrieval ---

export async function fetchRegions(): Promise<ApiResponse<Region[]>> {
  const res = await fetch(`${SERVICE_A_URL}/regions`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch regions');
  return res.json();
}

export async function fetchHistoricalData(regionId: string): Promise<ApiResponse<WaterReading[]>> {
  const res = await fetch(`${SERVICE_A_URL}/water-readings?region_id=${regionId}`, { 
    cache: 'no-store' 
  });
  if (!res.ok) throw new Error('Failed to fetch readings');
  return res.json();
}

export async function fetchForecasts(regionId: string): Promise<ApiResponse<Forecast[]>> {
  const res = await fetch(`${SERVICE_A_URL}/forecasts/${regionId}`, { 
    cache: 'no-store' 
  });
  if (!res.ok) throw new Error('Failed to fetch forecasts');
  return res.json();
}

// --- Orchestration (Proxied via Service A) ---

export async function triggerPipeline(date?: string) {
  // We send the request to Service A, which proxies it to Service B (Analytics)
  const payload = date ? { date } : {};

  const res = await fetch(`${SERVICE_A_URL}/pipeline/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const errorData = await res.json();
    // Handle both Python (FastAPI) 'detail' and Node (Express) 'message' error formats
    throw new Error(errorData.detail || errorData.message || 'Pipeline trigger failed');
  }
  return res.json();
}