import { defineConfig } from '@playwright/test'

// E2E-проверка идёт по реальному стеку (Docker LAN-стенд или боевой контур).
// Локально: .\scripts\start-lan.ps1, затем npm run test:e2e.
// В CI стенд поднимается шагом workflow, а браузер ставится npx playwright install.
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8080'

// В CI используется штатный Chromium; локально — установленный Edge,
// чтобы не скачивать браузеры на машине разработчика.
const channel = process.env.CI ? undefined : 'msedge'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL,
    channel,
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
