import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cacheVersionPlugin } from "./cacheVersionPlugin.mjs";
export default defineConfig({
  plugins: [react(), cacheVersionPlugin()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
