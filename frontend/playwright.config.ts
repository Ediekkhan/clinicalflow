import { defineConfig, devices } from '@playwright/test';

const browserTestDatabase = `sqlite+aiosqlite:////tmp/clinicalflow-playwright-${process.pid}-${Date.now()}.db`;
const browserNextDist = '.next-playwright';
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH ?? (process.platform === 'linux' ? '/tmp/chromium' : undefined);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:3100',
    trace: 'retain-on-failure',
    video: process.env.PLAYWRIGHT_RECORD_VIDEO === '1' ? 'on' : 'off',
    launchOptions: executablePath ? { executablePath } : undefined,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: '../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8100', cwd: '../backend', env: { APP_ENV: 'test', AUTH_RATE_LIMIT: '1000', ENABLE_TEST_FIXTURES: 'true', ENABLE_DEMO_CONTENT: 'true', AUTO_CREATE_SCHEMA: 'true', SKIP_PHONE_VERIFICATION: 'true', DATABASE_URL: browserTestDatabase, CORS_ORIGINS: 'http://127.0.0.1:3100' }, url: 'http://127.0.0.1:8100/health', reuseExistingServer: false, timeout: 120_000 },
    { command: 'npm run dev -- --hostname 127.0.0.1 --port 3100', cwd: '.', env: { NEXT_DIST_DIR: browserNextDist, NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8100' }, url: 'http://127.0.0.1:3100', reuseExistingServer: false, timeout: 120_000 },
  ],
});
