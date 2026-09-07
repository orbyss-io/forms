import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  forbidOnly: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.PROGRAMKIT_BASE_URL ?? 'http://localhost:5000',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
