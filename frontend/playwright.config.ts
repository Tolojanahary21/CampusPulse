import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const python = process.platform === 'win32'
  ? path.resolve('../backend/.venv/Scripts/python.exe')
  : path.resolve('../backend/.venv/bin/python');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: 'list',
  outputDir: '../.qa/playwright-results',
  use: {
    baseURL: 'http://localhost:3101',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
    ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}),
  },
  webServer: [
    {
      command: `"${python}" ../scripts/e2e_backend.py`,
      url: 'http://127.0.0.1:8001/health',
      reuseExistingServer: false,
      timeout: 90_000,
    },
    {
      command: 'npm run dev -- --port 3101',
      url: 'http://localhost:3101/login',
      env: { NEXT_PUBLIC_API_URL: 'http://localhost:8001/api/v1', NEXT_DIST_DIR: '.next-e2e' },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
