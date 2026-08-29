import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";
import { fileURLToPath, URL } from "node:url";
import { attachProxyErrorHandler, backendGuardPlugin } from "../scripts/vite-backend-guard";

const API_URL = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [
    backendGuardPlugin({
      apiUrl: API_URL,
      prefix: "/api",
      startHint: "cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload",
    }),
    vue(),
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: API_URL,
        changeOrigin: true,
        configure: (proxy) => attachProxyErrorHandler(proxy, API_URL),
      },
    },
  },
});
