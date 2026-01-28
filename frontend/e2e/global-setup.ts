/**
 * Playwright global setup for E2E tests.
 *
 * Creates a test user in Supabase using the Admin API and stores authenticated state
 * for reuse across all test files.
 *
 * This approach uses the Supabase service role key to programmatically create
 * the test user with auto-confirmed email, then logs in to capture session tokens.
 */

import { chromium, type FullConfig } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';
import path from 'path';
import fs from 'fs';

const TEST_USER = {
  email: process.env.E2E_TEST_EMAIL || 'e2e-test@pilotspace.dev',
  password: process.env.E2E_TEST_PASSWORD || 'TestPassword123!',
  name: 'E2E Test User',
};

const AUTH_STATE_PATH = path.join(__dirname, '.auth/user.json');

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://localhost:18000';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

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

  // Validate required environment variables
  if (!SUPABASE_SERVICE_KEY) {
    console.error('❌ SUPABASE_SERVICE_ROLE_KEY not found in environment');
    console.log('   Set it in frontend/.env.local to enable E2E authentication');
    createEmptyAuthState();
    return;
  }

  if (!SUPABASE_ANON_KEY) {
    console.error('❌ NEXT_PUBLIC_SUPABASE_ANON_KEY not found in environment');
    console.log('   Set it in frontend/.env.local to enable E2E authentication');
    createEmptyAuthState();
    return;
  }

  console.log('🔧 Global setup: Using Supabase Admin API to create test user');
  console.log(`   Supabase URL: ${SUPABASE_URL}`);
  console.log(`   Test user: ${TEST_USER.email}`);

  try {
    // Step 1: Create admin client with service role key
    const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    // Step 2: Create test user with auto-confirmed email (bypasses confirmation)
    console.log('📝 Global setup: Creating test user with admin API...');
    const { data: user, error: createError } = await supabaseAdmin.auth.admin.createUser({
      email: TEST_USER.email,
      password: TEST_USER.password,
      email_confirm: true, // Auto-confirm email
      user_metadata: {
        name: TEST_USER.name,
      },
    });

    let userId: string | undefined;

    if (createError) {
      // Check if user already exists (common case - ignore error)
      const errorMsg = createError.message.toLowerCase();
      if (
        errorMsg.includes('already registered') ||
        errorMsg.includes('email_exists') ||
        createError.code === 'email_exists'
      ) {
        console.log('✅ Global setup: Test user already exists');

        // Get existing user and confirm their email
        console.log('🔧 Global setup: Confirming email for existing user...');
        const { data: existingUsers } = await supabaseAdmin.auth.admin.listUsers();
        const existingUser = existingUsers?.users.find((u) => u.email === TEST_USER.email);

        if (existingUser) {
          userId = existingUser.id;

          // Update user to confirm email
          await supabaseAdmin.auth.admin.updateUserById(existingUser.id, {
            email_confirm: true,
          });
          console.log('✅ Global setup: Email confirmed for existing user');
        }
      } else {
        console.error('❌ Global setup: Failed to create user:', createError);
        createEmptyAuthState();
        return;
      }
    } else {
      console.log('✅ Global setup: Test user created successfully');
      userId = user?.user?.id;
    }

    // Step 3: Login as test user with anon client to get session tokens
    console.log('🔐 Global setup: Logging in to capture session tokens...');
    const supabaseAnon = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    const { data: sessionData, error: loginError } = await supabaseAnon.auth.signInWithPassword({
      email: TEST_USER.email,
      password: TEST_USER.password,
    });

    if (loginError || !sessionData.session) {
      console.error('❌ Global setup: Failed to login:', loginError);
      createEmptyAuthState();
      return;
    }

    console.log('✅ Global setup: Login successful, session captured');

    // Step 4: Set up browser with auth session in localStorage
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    // Navigate to the app to establish origin
    await page.goto(baseURL, { waitUntil: 'domcontentloaded' });

    // Inject Supabase session into localStorage
    // Supabase stores session in localStorage with key pattern: sb-{project-ref}-auth-token
    const storageKey = `sb-localhost-auth-token`; // For local development
    await page.evaluate(
      ({ key, session }) => {
        localStorage.setItem(key, JSON.stringify(session));
      },
      { key: storageKey, session: sessionData.session }
    );

    console.log('✅ Global setup: Auth session injected into localStorage');

    // Save storage state to file
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log(`✅ Global setup: Auth state saved to ${AUTH_STATE_PATH}`);

    await browser.close();

    // Verify auth state file has content
    const authState = JSON.parse(fs.readFileSync(AUTH_STATE_PATH, 'utf-8'));
    const hasOrigins = authState.origins && authState.origins.length > 0;
    const hasLocalStorage = hasOrigins && authState.origins[0].localStorage;

    if (hasLocalStorage && hasLocalStorage.length > 0) {
      console.log('✅ Global setup: Auth state verified - localStorage contains session');
    } else {
      console.log('⚠️ Global setup: Auth state may be incomplete - no localStorage entries found');
    }
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    console.log('   Tests will run with empty auth state.');
    createEmptyAuthState();
  }
}

export { TEST_USER, AUTH_STATE_PATH };
