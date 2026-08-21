import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const readFrontendFile = (relativePath) =>
  readFileSync(resolve(process.cwd(), relativePath), "utf8");

describe("EAROS Vite client ownership", () => {
  it("uses the EAROS-owned module entry point without inherited vendor scripts", () => {
    const indexHtml = readFrontendFile("index.html");

    expect(indexHtml).toContain('<script type="module" src="/src/index.js"></script>');
    expect(indexHtml).not.toMatch(/assets\.emergent\.sh|emergent-main\.js|react-scripts|static\/js\/bundle/i);
  });

  it("does not retain retired Create React App or Webpack build-chain packages and resolutions", () => {
    const packageJson = JSON.parse(readFrontendFile("package.json"));
    const dependencies = packageJson.dependencies ?? {};
    const resolutions = packageJson.resolutions ?? {};

    expect(dependencies["react-scripts"]).toBeUndefined();
    expect(dependencies["cra-template"]).toBeUndefined();
    expect(resolutions).not.toHaveProperty("webpack-dev-server");
    expect(resolutions).not.toHaveProperty("resolve-url-loader");
    expect(resolutions).not.toHaveProperty("**/resolve-url-loader/postcss");
    expect(resolutions).not.toHaveProperty("**/webpack-dev-server/ws");
    expect(resolutions).not.toHaveProperty("**/css-loader/postcss");
    expect(resolutions).not.toHaveProperty("**/css-minimizer-webpack-plugin/postcss");
    expect(resolutions).not.toHaveProperty("**/react-scripts/postcss");
    expect(packageJson.scripts).toMatchObject({
      dev: "vite",
      build: "vite build",
      preview: "vite preview",
    });
  });

  it("fails closed on unsafe production API-origin configuration before bundling", () => {
    const viteConfig = readFrontendFile("vite.config.mjs");
    const apiClient = readFrontendFile("src/lib/api.js");

    expect(viteConfig).toContain('import { defineConfig, loadEnv } from "vite";');
    expect(viteConfig).toContain("allowInsecureLocalhost: env.VITE_EAROS_ALLOW_INSECURE_LOCAL_SMOKE === \"true\"");
    expect(apiClient).toContain('allowInsecureLocalhost: import.meta.env.VITE_EAROS_ALLOW_INSECURE_LOCAL_SMOKE === "true"');
  });
});
