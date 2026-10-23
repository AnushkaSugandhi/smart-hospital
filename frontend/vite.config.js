import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts (with its d3 deps) is ~530 kB on its own; it is split out and cached separately.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["recharts"],
          motion: ["framer-motion"],
        },
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
