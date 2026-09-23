import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

const backendUrl = process.env.VITE_BACKEND_URL || "http://localhost:8000";
const proxy = {
  "/api": { target: backendUrl, changeOrigin: true },
  "/hls": { target: backendUrl, changeOrigin: true },
  "/health": { target: backendUrl, changeOrigin: true },
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy,
  },
  preview: {
    port: 3000,
    host: true,
    proxy,
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes("node_modules")) {
            if (id.includes("@vidstack")) {
              return "vendor-player";
            }
            if (id.includes("react-markdown") || id.includes("remark-gfm")) {
              return "vendor-markdown";
            }
            if (id.includes("lucide-react")) {
              return "vendor-icons";
            }
            if (
              id.includes("react") ||
              id.includes("react-dom") ||
              id.includes("react-router-dom")
            ) {
              return "vendor-react";
            }
          }
        },
      },
    },
  },
});
