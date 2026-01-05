// src/lib/api.ts
import { Region, WaterReading, Forecast, ApiResponse } from '@/types';

const SERVICE_A_URL = process.env.NEXT_PUBLIC_SERVICE_A_URL || 'http://localhost:4000/api/v1';
const SERVICE_C_URL = process.env.NEXT_PUBLIC_SERVICE_C_URL || 'http://localhost:8002';

// --- Service A: Data Retrieval ---

export async function fetchRegions(): Promise<ApiResponse<Region[]>> {
  const res = await fetch(`${SERVICE_A_URL}/regions`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch regions');
  return res.json();
}

export async function fetchHistoricalData(regionId: string): Promise<ApiResponse<WaterReading[]>> {
  // Fetch only active readings for the specific region
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

// --- Service C: Orchestration ---

export async function triggerPipeline() {
  const res = await fetch(`${SERVICE_C_URL}/pipeline/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Pipeline trigger failed');
  }
  return res.json();
}