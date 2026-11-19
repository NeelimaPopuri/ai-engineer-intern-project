import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  // Reads ../.env so the API key is injected by the dev proxy and never ships in the bundle.
  const env = loadEnv(mode, "..", "");
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5174,
      proxy: {
        "/api": {
          target: "http://localhost:8001",
          headers: { "X-API-Key": env.APP_API_KEY || "" },
        },
      },
    },
  };
});
