import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => ({
  plugins: [react({ include: /\.[jt]sx?$/ })],
  resolve: {
    alias: {
      "@": path.resolve(rootDir, "src"),
    },
  },
  server: {
    host: true,
    strictPort: true,
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
}));
