import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

const backendUrl = process.env.VITE_BACKEND_URL || "http://localhost:8000";
const proxy = {
  "/api": { target: backendUrl, changeOrigin: true },
  "/hls": { target: backendUrl, changeOrigin: true },
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
});
