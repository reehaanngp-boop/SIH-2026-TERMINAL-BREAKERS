import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Development server proxies API calls to the FastAPI backend so the SPA and
// backend can run side-by-side with zero CORS config.
// Production build output goes to backend/app/static which FastAPI serves.
const buildTimestamp = Date.now();

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: process.env.CF_PAGES ? "dist" : fileURLToPath(new URL("../backend/app/static", import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v${buildTimestamp}.js`,
        chunkFileNames: `assets/[name]-v${buildTimestamp}.js`,
        assetFileNames: `assets/[name]-v${buildTimestamp}.[ext]`,
      },
    },
  },
});
