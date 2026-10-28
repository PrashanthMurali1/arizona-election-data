import { defineConfig } from "@playwright/test";
const python =
  process.platform === "win32"
    ? "../.venv/Scripts/python.exe"
    : "../.venv/bin/python";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173", headless: true },
  reporter: "list",
  webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : [
    {
      command: `${python} -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8000`,
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
    },
  ],
});
