import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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
