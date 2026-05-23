import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Relative base so asset paths work under HA Ingress (which prefixes the URL)
  base: "./",
  server: {
    host: "0.0.0.0",
    proxy: {
      "/api": "http://localhost:8000",
      "/oauth": "http://localhost:8000",
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
      },
    },
  },
});
