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
const SEED_CONTEXT_PATH = path.join(__dirname, '.auth/seed-context.json');

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

    // Step 5: Create default workspace if it doesn't exist
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const token = sessionData.session.access_token;

    console.log('🔧 Global setup: Ensuring default workspace exists...');
    const wsListRes = await fetch(`${API_URL}/workspaces`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const wsList = await wsListRes.json();
    const hasWorkspace = wsList.items?.some((w: { slug: string }) => w.slug === 'workspace');

    if (!hasWorkspace) {
      console.log('📝 Global setup: Creating "workspace" workspace...');
      const createRes = await fetch(`${API_URL}/workspaces`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'Pilot Space',
          slug: 'workspace',
          description: 'E2E test workspace',
        }),
      });

      if (createRes.ok) {
        console.log('✅ Global setup: Workspace created successfully');
      } else if (createRes.status === 409) {
        console.log('✅ Global setup: Workspace already exists (409)');
      } else {
        const errBody = await createRes.text();
        console.warn(
          `⚠️ Global setup: Workspace creation returned ${createRes.status}: ${errBody}`
        );
      }
    } else {
      console.log('✅ Global setup: Workspace "workspace" already exists');
    }

    // Save storage state to file
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log(`✅ Global setup: Auth state saved to ${AUTH_STATE_PATH}`);

    await browser.close();

    // Phase 94 Plan 03 — write seed-context.json so capstone E2E specs
    // can resolve workspace + entity ids without hardcoding. Best-effort:
    // - Topic chain (root + 2 children + 5-deep chain) is seeded via the
    //   public /workspaces/{ws}/notes + /move endpoints.
    // - Chat/proposal/task entities require AI/FK fan-out and stay null
    //   until a backend test-seed endpoint is added (follow-up).
    const workspaceId = (() => {
      const matched = wsList.items?.find?.(
        (w: { slug: string; id?: string }) => w.slug === 'workspace'
      );
      return matched?.id ?? null;
    })();

    const topicSeed = workspaceId
      ? await seedTopicChain({ apiUrl: API_URL, token, workspaceId })
      : { rootTopicId: null, childTopicAId: null, childTopicBId: null, deepTopicId: null };

    const seedCtx = {
      workspaceSlug: 'workspace',
      workspaceId: workspaceId ?? '',
      ...topicSeed,
      taskId: null,
      chatSessionId: null,
      artifactId: null,
      pendingProposalId: null,
      skillSlug: null,
      skillReferenceFilePath: null,
    };
    fs.writeFileSync(SEED_CONTEXT_PATH, JSON.stringify(seedCtx, null, 2));
    console.log(`✅ Global setup: Seed context written to ${SEED_CONTEXT_PATH}`);

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

interface TopicSeedResult {
  rootTopicId: string | null;
  childTopicAId: string | null;
  childTopicBId: string | null;
  /** Topic at depth=5 — drop targets here would push to depth=6 (max-depth error). */
  deepTopicId: string | null;
}

interface TopicSeedDeps {
  apiUrl: string;
  token: string;
  workspaceId: string;
}

/**
 * Seed the topic-tree fixtures consumed by topic-drag-drop.spec.ts.
 *
 * Layout produced (idempotent — looks up `[E2E SEED]` titles before creating):
 *
 *   root (depth 0)
 *   ├── childA (depth 1)
 *   ├── childB (depth 1)
 *   └── deep1 (depth 1)
 *       └── deep2 (depth 2)
 *           └── deep3 (depth 3)
 *               └── deep4 (depth 4)
 *                   └── deep5 (depth 5)   ← deepTopicId
 *
 * Returns nulls for any rung that fails so the spec falls back to test.skip.
 */
async function seedTopicChain({
  apiUrl,
  token,
  workspaceId,
}: TopicSeedDeps): Promise<TopicSeedResult> {
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  async function findExisting(title: string): Promise<string | null> {
    const res = await fetch(
      `${apiUrl}/workspaces/${workspaceId}/notes?q=${encodeURIComponent(title)}&pageSize=5`,
      { headers: { Authorization: headers.Authorization } }
    );
    if (!res.ok) return null;
    const body = (await res.json()) as { items?: Array<{ id: string; title: string }> };
    return body.items?.find((n) => n.title === title)?.id ?? null;
  }

  async function createTopic(title: string): Promise<string | null> {
    const existing = await findExisting(title);
    if (existing) return existing;
    const res = await fetch(`${apiUrl}/workspaces/${workspaceId}/notes`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      console.warn(`⚠️ Topic seed: create "${title}" → ${res.status}`);
      return null;
    }
    const body = (await res.json()) as { id?: string };
    return body.id ?? null;
  }

  async function reparent(noteId: string, parentId: string | null): Promise<boolean> {
    const res = await fetch(`${apiUrl}/workspaces/${workspaceId}/notes/${noteId}/move`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ parentId }),
    });
    if (!res.ok) {
      const text = await res.text();
      console.warn(`⚠️ Topic seed: reparent ${noteId}→${parentId} → ${res.status} ${text}`);
    }
    return res.ok;
  }

  console.log('🔧 Global setup: Seeding topic chain (root + 2 children + 5-deep)…');

  const rootTopicId = await createTopic('[E2E SEED] Root');
  if (!rootTopicId) return { rootTopicId: null, childTopicAId: null, childTopicBId: null, deepTopicId: null };

  const childTopicAId = await createTopic('[E2E SEED] Child A');
  const childTopicBId = await createTopic('[E2E SEED] Child B');
  if (childTopicAId) await reparent(childTopicAId, rootTopicId);
  if (childTopicBId) await reparent(childTopicBId, rootTopicId);

  // 5-deep chain: deep1 (under root) → deep5 (depth=5)
  const deepTitles = ['[E2E SEED] Deep 1', '[E2E SEED] Deep 2', '[E2E SEED] Deep 3', '[E2E SEED] Deep 4', '[E2E SEED] Deep 5'];
  let parent: string | null = rootTopicId;
  let lastId: string | null = null;
  for (const title of deepTitles) {
    const id = await createTopic(title);
    if (!id) {
      lastId = null;
      break;
    }
    const ok = await reparent(id, parent);
    if (!ok) {
      lastId = null;
      break;
    }
    parent = id;
    lastId = id;
  }

  console.log(
    `✅ Global setup: Topic seed → root=${rootTopicId?.slice(0, 8)} childA=${childTopicAId?.slice(0, 8)} childB=${childTopicBId?.slice(0, 8)} deep5=${lastId?.slice(0, 8)}`
  );

  return {
    rootTopicId,
    childTopicAId,
    childTopicBId,
    deepTopicId: lastId,
  };
}

export { TEST_USER, AUTH_STATE_PATH };
