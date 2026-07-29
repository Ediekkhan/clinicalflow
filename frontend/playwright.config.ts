import { defineConfig, devices } from '@playwright/test';

const browserTestDatabase = `sqlite+aiosqlite:///C:/tmp/clinicalflow-playwright-${process.pid}.db`;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45_000,
  fullyParallel: false,
  retries: 0,
  reporter: 'line',
  use: { baseURL: 'http://127.0.0.1:3100', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8100', cwd: '../backend', env: { APP_ENV: 'test', ENABLE_TEST_FIXTURES: 'true', DATABASE_URL: browserTestDatabase, CORS_ORIGINS: 'http://127.0.0.1:3100' }, url: 'http://127.0.0.1:8100/health', reuseExistingServer: false, timeout: 120_000 },
    { command: 'npm run dev -- --hostname 127.0.0.1 --port 3100', cwd: '.', env: { NEXT_DIST_DIR: '.next-playwright', NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8100' }, url: 'http://127.0.0.1:3100', reuseExistingServer: false, timeout: 120_000 },
  ],
});
