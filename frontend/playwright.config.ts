import { defineConfig, devices } from '@playwright/test';

const browserTestDatabase = `sqlite+aiosqlite:////tmp/clinicalflow-playwright-${process.pid}.db`;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  fullyParallel: false,
  retries: 0,
  reporter: 'line',
  use: { baseURL: 'http://127.0.0.1:3000', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: 'PYTHONPATH=. /usr/local/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000', cwd: '../backend', env: { DATABASE_URL: browserTestDatabase }, url: 'http://127.0.0.1:8000/health', reuseExistingServer: false, timeout: 120_000 },
    { command: 'npm run dev -- --hostname 127.0.0.1 --port 3000', cwd: '.', url: 'http://127.0.0.1:3000', reuseExistingServer: false, timeout: 120_000 },
  ],
});
