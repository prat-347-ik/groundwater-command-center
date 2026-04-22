import axios from 'axios';
import { ExtractionLog } from '@/types'; // Ensure you have this type defined in types/index.ts

// --- Configuration ---
// These match the ports we defined in your backend services
const toApiV1Base = (value: string) => {
  const trimmed = value.replace(/\/+$/, '');
  return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`;
};

const resolveDefaultHost = () => {
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}`;
  }

  return 'http://localhost';
};

const resolveApiBase = (port: number, ...candidates: Array<string | undefined>) => {
  const explicit = candidates.find(Boolean);
  if (explicit) {
    return toApiV1Base(explicit);
  }

  return toApiV1Base(`${resolveDefaultHost()}:${port}`);
};

const OPS_URL = resolveApiBase(
  4000,
  process.env.NEXT_PUBLIC_OPS_URL,
  process.env.NEXT_PUBLIC_API_URL_A
);

const ANALYTICS_URL = resolveApiBase(
  8000,
  process.env.NEXT_PUBLIC_ANALYTICS_URL,
  process.env.NEXT_PUBLIC_API_URL_B
);

const CLIMATE_URL = resolveApiBase(
  8100,
  process.env.NEXT_PUBLIC_CLIMATE_URL,
  process.env.NEXT_PUBLIC_API_URL_C
);

export const getApiErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const responseMessage =
      (typeof error.response?.data === 'string' && error.response.data) ||
      (error.response?.data as any)?.message ||
      (error.response?.data as any)?.error;

    if (responseMessage) {
      return responseMessage;
    }

    if (!error.response) {
      return 'Service unreachable. Please verify backend services are running.';
    }

    return `Request failed with status ${error.response.status}.`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unexpected error occurred.';
};

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
  if (axios.isAxiosError(error) && !error.response) {
    // Browser couldn't reach the service (down/unavailable/CORS/network interruption)
    console.warn("API Network Warning:", {
      message: error.message,
      code: error.code,
      method: error.config?.method,
      url: error.config?.url,
      baseURL: error.config?.baseURL,
    });
    return Promise.reject(error);
  }

  console.error("API Error:", getApiErrorMessage(error));
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