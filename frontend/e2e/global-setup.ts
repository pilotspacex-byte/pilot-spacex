/**
 * Playwright global setup for E2E tests.
 *
 * Creates a test user in Supabase and stores authenticated state
 * for reuse across all test files.
 *
 * NOTE: For local development, disable email confirmation in Supabase:
 * Supabase Dashboard -> Authentication -> Email -> Disable "Confirm email"
 */

import { chromium, type FullConfig } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const TEST_USER = {
  email: process.env.E2E_TEST_EMAIL || 'e2e-test@pilotspace.dev',
  password: process.env.E2E_TEST_PASSWORD || 'TestPassword123!',
  name: 'E2E Test User',
};

const AUTH_STATE_PATH = path.join(__dirname, '.auth/user.json');

// Ensure .auth directory exists
function ensureAuthDir(): void {
  const authDir = path.dirname(AUTH_STATE_PATH);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
}

// Create empty auth state file so tests can run (unauthenticated)
function createEmptyAuthState(): void {
  ensureAuthDir();
  const emptyState = {
    cookies: [],
    origins: [],
  };
  fs.writeFileSync(AUTH_STATE_PATH, JSON.stringify(emptyState, null, 2));
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const { baseURL } = config.projects[0].use;

  if (!baseURL) {
    throw new Error('baseURL not configured in playwright.config.ts');
  }

  // Create empty auth state as fallback
  createEmptyAuthState();

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login page
    await page.goto(`${baseURL}/login`, { waitUntil: 'networkidle' });

    // Check if we're already on a logged-in page (from previous state)
    const currentUrl = page.url();
    if (!currentUrl.includes('/login') && !currentUrl.includes('/signup')) {
      console.log('✅ Global setup: Already authenticated');
      await context.storageState({ path: AUTH_STATE_PATH });
      await browser.close();
      return;
    }

    // Check if login page loaded
    const emailInput = page.locator('#email');
    const hasLoginForm = await emailInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasLoginForm) {
      console.log('⚠️ Global setup: Login form not found, using empty auth state');
      await browser.close();
      return;
    }

    // Try to login first (user may already exist)
    console.log('🔐 Global setup: Attempting login with test user...');
    await page.fill('#email', TEST_USER.email);
    await page.fill('#password', TEST_USER.password);
    await page.click('button[type="submit"]');

    // Wait for either success redirect or error
    const result = await Promise.race([
      page
        .waitForURL((url) => !url.pathname.includes('/login'), { timeout: 8000 })
        .then(() => 'success'),
      page.waitForSelector('.bg-destructive\\/10', { timeout: 8000 }).then(() => 'error'),
    ]).catch(() => 'timeout');

    if (result === 'success') {
      // Login succeeded, save auth state
      await page.waitForLoadState('networkidle');
      await context.storageState({ path: AUTH_STATE_PATH });
      console.log('✅ Global setup: Logged in existing test user');
      await browser.close();
      return;
    }

    // User doesn't exist or wrong password, try to sign up
    console.log('📝 Global setup: Login failed, trying to create new test user...');

    // The login and signup are on the same page - click "Sign up" button to toggle
    const signupToggle = page.getByRole('button', { name: 'Sign up' });
    await signupToggle.click();

    // Wait for name field to appear (indicates signup mode)
    const nameInput = page.locator('#name');
    const hasNameField = await nameInput.isVisible({ timeout: 3000 }).catch(() => false);

    if (!hasNameField) {
      console.log('⚠️ Global setup: Signup form not found, using empty auth state');
      await browser.close();
      return;
    }

    // Fill signup form
    await page.fill('#name', TEST_USER.name);
    // Email and password may still be filled from previous attempt, clear and re-fill
    await page.fill('#email', TEST_USER.email);
    await page.fill('#password', TEST_USER.password);
    await page.click('button[type="submit"]');

    // Wait for result
    const signupResult = await Promise.race([
      page
        .waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 })
        .then(() => 'success'),
      page.waitForSelector('text=Check your email', { timeout: 5000 }).then(() => 'confirmation'),
      page.waitForSelector('text=already registered', { timeout: 5000 }).then(() => 'exists'),
      page.waitForSelector('.bg-destructive\\/10', { timeout: 5000 }).then(() => 'error'),
    ]).catch(() => 'timeout');

    if (signupResult === 'success') {
      await page.waitForLoadState('networkidle');
      await context.storageState({ path: AUTH_STATE_PATH });
      console.log('✅ Global setup: Created and logged in test user');
    } else if (signupResult === 'confirmation') {
      console.log('⚠️ Global setup: Email confirmation required.');
      console.log('   To run E2E tests with authentication:');
      console.log('   1. Go to Supabase Dashboard -> Authentication -> Email');
      console.log('   2. Disable "Confirm email" option');
      console.log('   3. Run tests again');
      console.log('   Tests will run but authentication-required features will fail.');
    } else if (signupResult === 'exists') {
      console.log('⚠️ Global setup: User exists with different credentials.');
      console.log('   Set E2E_TEST_EMAIL and E2E_TEST_PASSWORD environment variables.');
    } else {
      console.log('⚠️ Global setup: Signup timed out or failed');
      // Try to get error message
      const errorMsg = await page
        .locator('.bg-destructive\\/10')
        .textContent()
        .catch(() => null);
      if (errorMsg) {
        console.log(`   Error: ${errorMsg}`);
      }
    }
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    console.log('   Tests will run with empty auth state.');
  } finally {
    await browser.close();
  }
}

export { TEST_USER, AUTH_STATE_PATH };
