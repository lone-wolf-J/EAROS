import axios from "axios";

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");

if (import.meta.env.PROD && !BACKEND_URL) {
  throw new Error("VITE_BACKEND_URL must be set for an EAROS production client build.");
}

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
