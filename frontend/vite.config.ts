import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Development server proxies API calls to the FastAPI backend so the SPA and
// backend can run side-by-side with zero CORS config.
// Production build output goes to backend/app/static which FastAPI serves.
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
      },
    },
  },
  build: {
    outDir: fileURLToPath(new URL("../backend/app/static", import.meta.url)),
    emptyOutDir: true,
    sourcemap: false,
  },
});
