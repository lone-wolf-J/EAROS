import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveBackendUrl } from "./src/lib/backendUrl.js";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (mode === "production") {
    resolveBackendUrl(env.VITE_BACKEND_URL, { production: true });
  }

  return {
  plugins: [react({ include: /\.[jt]sx?$/ })],
  resolve: {
    alias: {
      "@": path.resolve(rootDir, "src"),
    },
  },
  server: {
    host: true,
    strictPort: true,
    allowedHosts: [".manus.computer"],
  },
  esbuild: {
    loader: "jsx",
    include: /src\/.*\.(js|jsx)$/,
    exclude: [],
  },
  optimizeDeps: {
    entries: ["index.html"],
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
  build: {
    sourcemap: mode !== "production",
    target: "es2022",
    outDir: "dist",
    emptyOutDir: true,
  },
};
});
