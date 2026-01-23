import axios from 'axios';
import { ExtractionLog } from '@/types'; // Ensure you have this type defined in types/index.ts

// --- Configuration ---
// These match the ports we defined in your backend services
const OPS_URL = process.env.NEXT_PUBLIC_OPS_URL || 'http://localhost:4000/api/v1';
const ANALYTICS_URL = process.env.NEXT_PUBLIC_ANALYTICS_URL || 'http://localhost:8000/api/v1';
const CLIMATE_URL = process.env.NEXT_PUBLIC_CLIMATE_URL || 'http://localhost:8100/api/v1';

// --- 1. Service A: Operations (Node.js) ---
export const opsClient = axios.create({
  baseURL: OPS_URL,
  headers: { 'Content-Type': 'application/json' }
});

// --- 2. Service B: Analytics (Python/Random Forest) ---
export const analyticsClient = axios.create({
  baseURL: ANALYTICS_URL,
  headers: { 'Content-Type': 'application/json' }
});

// --- 3. Service C: Climate (Python/FastAPI) ---
export const climateClient = axios.create({
  baseURL: CLIMATE_URL,
  headers: { 'Content-Type': 'application/json' }
});

// --- Unified Error Handling ---
// This ensures your UI doesn't crash if a microservice is down
const handleApiError = (error: any) => {
  console.error("API Error:", error.response?.data || error.message);
  return Promise.reject(error);
};

opsClient.interceptors.response.use((r) => r, handleApiError);
analyticsClient.interceptors.response.use((r) => r, handleApiError);
climateClient.interceptors.response.use((r) => r, handleApiError);

// ==========================================
// 💧 Extraction & Operations API
// ==========================================

// Get history of extractions for a specific region
export const getExtractionHistory = async (regionId: string) => {
  // Matches GET /api/v1/extraction/:region_id
  const response = await opsClient.get<{success: boolean, data: ExtractionLog[]}>(`/extraction/${regionId}`);
  return response.data.data;
};

// Log a new extraction event
export const createExtractionLog = async (data: { region_id: string; volume_liters: number; usage_type: string }) => {
  // Matches POST /api/v1/extraction
  const response = await opsClient.post('/extraction', data);
  return response.data;
};

// Get water readings (for correlation charts)
export const getWaterReadings = async (regionId: string) => {
  // Matches GET /api/v1/water-readings?region_id=...
  const response = await opsClient.get(`/water-readings?region_id=${regionId}&limit=100`);
  return response.data.data; 
};

// Get static region details (for Safe Yield limits)
export const getRegionDetails = async (regionId: string) => {
  // Matches GET /api/v1/regions/:id
  const response = await opsClient.get(`/regions/${regionId}`);
  return response.data;
};