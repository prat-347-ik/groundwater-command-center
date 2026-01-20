// --- Region (Service A) ---
export interface Region {
  region_id: string;
  name: string;
  state: string;
  critical_water_level_m: number;
  aquifer_area_m2: number;
  specific_yield: number;
  is_active: boolean;
}

// --- Forecast (Service B) ---
export interface Forecast {
  region_id: string;
  forecast_date: string;
  predicted_level: number;
  horizon_step: number;
  scenario_extraction: number; // For the "What-If" simulator
  model_version: string;
}

// --- Water Reading (Service A) ---
export interface WaterReading {
  _id?: string;
  region_id: string;
  well_id: string;
  timestamp: string;
  water_level: number;
  is_suspicious: boolean;
  anomaly_reason?: string;
}

// --- Extraction Log (Service A) ---
export interface ExtractionLog {
  region_id: string;
  volume_liters: number;
  usage_type: string;
  timestamp: string;
}