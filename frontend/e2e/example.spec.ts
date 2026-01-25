import { expect, test } from '@playwright/test';

test.describe('Pilot Space Home', () => {
  test('should load the home page', async ({ page }) => {
    await page.goto('/');

    // Wait for the page to load
    await expect(page).toHaveTitle(/Pilot Space/);
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');

    // Basic accessibility check - page should be keyboard navigable
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});
