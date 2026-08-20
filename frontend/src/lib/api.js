import axios from "axios";
import { resolveBackendUrl } from "./backendUrl";

export { resolveBackendUrl } from "./backendUrl";

const BACKEND_URL = resolveBackendUrl(import.meta.env.VITE_BACKEND_URL, {
  production: import.meta.env.PROD,
});

export const API = `${BACKEND_URL}/api`;

// Axios instance with credentials so httpOnly session cookies flow.
export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // Let callers handle 401 (auth context redirects).
    return Promise.reject(err);
  },
);
