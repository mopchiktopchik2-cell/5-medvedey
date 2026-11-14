import { defineConfig } from '@playwright/test'

// E2E-проверка идёт по реальному стеку (Docker LAN-стенд или боевой контур).
// Перед запуском: .\scripts\start-lan.ps1, затем npm run test:e2e.
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8080'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL,
    // На Windows используем установленный Edge — не нужно скачивать браузеры.
    channel: process.env.E2E_CHANNEL ?? 'msedge',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
