import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The production build goes straight into the Python package so the server can
// serve it.  During development, /api and /ws are proxied to the Python server
// (start it with `python -m backend.main`, default port 8000).
const target = process.env.PHONEPAD_SERVER ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../backend/static",
    emptyOutDir: true,
    target: "es2020",
  },
  server: {
    host: "0.0.0.0",
    proxy: {
      "/api": target,
      "/ws": { target: target.replace(/^http/, "ws"), ws: true },
    },
  },
});
