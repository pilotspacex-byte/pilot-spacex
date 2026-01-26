/**
 * Playwright auth fixtures for E2E tests.
 *
 * Provides reusable authentication setup for tests that require
 * authenticated user context.
 */

import { test as base, expect } from '@playwright/test';
import path from 'path';

const AUTH_STATE_PATH = path.join(__dirname, '.auth/user.json');

const TEST_USER = {
  email: 'e2e-test@pilotspace.dev',
  password: 'TestPassword123!',
  name: 'E2E Test User',
};

/**
 * Extended test with authenticated user context.
 * Uses stored auth state from global setup.
 */
export const test = base.extend<{
  authenticatedPage: typeof base;
}>({
  // Override storageState to use auth state file
  // Note: This is a Playwright fixture, not a React hook
  // The 'use' function is part of Playwright's test API
  storageState: async ({}, use) => {
    // Try to use stored auth state, fall back to default if not found
    // eslint-disable-next-line react-hooks/rules-of-hooks -- This is Playwright's 'use' function, not a React hook
    await use(AUTH_STATE_PATH).catch(() => use(undefined));
  },
});

/**
 * Login helper for tests that need fresh authentication.
 */
export async function loginAsTestUser(page: typeof base.prototype.page): Promise<boolean> {
  await page.goto('/login');

  // Fill login form
  await page.fill('#email', TEST_USER.email);
  await page.fill('#password', TEST_USER.password);
  await page.click('button[type="submit"]');

  // Wait for redirect or error
  try {
    await page.waitForURL(/\/(pilot-space-demo|workspace|$)/, { timeout: 10000 });
    return true;
  } catch {
    // Check for error message
    const errorVisible = await page.locator('text=Invalid').isVisible();
    if (errorVisible) {
      console.error('Login failed: Invalid credentials');
    }
    return false;
  }
}

/**
 * Signup helper for tests that need to create a new user.
 */
export async function signupUser(
  page: typeof base.prototype.page,
  user: { email: string; password: string; name: string }
): Promise<boolean> {
  await page.goto('/login');

  // Click sign up link
  await page.click('text=Sign up');

  // Wait for signup form
  await page.waitForSelector('#name');

  // Fill signup form
  await page.fill('#name', user.name);
  await page.fill('#email', user.email);
  await page.fill('#password', user.password);
  await page.click('button[type="submit"]');

  try {
    await page.waitForURL(/\/(pilot-space-demo|workspace|$)/, { timeout: 10000 });
    return true;
  } catch {
    return false;
  }
}

export { expect, TEST_USER, AUTH_STATE_PATH };
