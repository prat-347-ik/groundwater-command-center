// src/types/index.ts

export interface Region {
  _id: string;
  region_id: string;      // e.g., "region-001"
  name: string;           // e.g., "California Central Valley"
  state: string;          // e.g., "California"
  critical_level: number; // Threshold for alerts
  // coordinates: { ... }  <-- REMOVED: Not provided by Service A
  is_active: boolean;
}

export interface WaterReading {
  _id: string;
  region_id: string;
  well_id: string;
  timestamp: string;      // ISO Date String
  water_level: number;    // Depth in meters
}

export interface Forecast {
  _id: string;
  region_id: string;
  forecast_date: string;  // ISO Date String
  predicted_level: number;
  horizon_step: number;   // 1-7 days ahead
}

// Generic response wrapper for Service A
export interface ApiResponse<T> {
  success: boolean;
  count?: number;
  data: T;
}


export interface RainfallReading {
  _id?: string;
  region_id: string;
  timestamp: string;
  amount_mm: number;
  source: string;
}

export interface SystemHealth {
  service: string;
  status: 'UP' | 'DOWN';
  timestamp: string;
}

export interface JobResponse {
  status: string;
  job: string;
  message?: string;
}

export interface ApiResponse<T> {
  count?: number;
  data: T;
  message?: string;
}