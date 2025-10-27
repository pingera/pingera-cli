const { test, expect } = require('@playwright/test');

test('Basic Screenshot', async ({ page }) => {
  // Navigate to the page
  await page.goto('https://playwright.dev/');

  // Wait for the page to be in a stable state (e.g., network idle)
  await page.waitForLoadState('load');

  // Take a full-page screenshot
  await page.screenshot({ path: 'screenshot.png', fullPage: true });

  console.log('Successfully took a full-page screenshot.');
});
