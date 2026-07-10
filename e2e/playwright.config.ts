import { defineConfig } from '@playwright/test';

// Прогон против собранного приложения (docker compose up или uvicorn + frontend/dist)
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:8000',
  },
});
