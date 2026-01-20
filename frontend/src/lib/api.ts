import axios from 'axios';

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