# Supabase Authentication Fix Report

**Date**: 2026-01-28
**Status**: ✅ **Supabase Configured** | ⚠️ **Auth State Still Empty**
**Progress**: MAILER_AUTOCONFIRM enabled, tests running

---

## ✅ Fixes Applied

### 1. Supabase Email Auto-Confirmation Enabled

**File**: `infra/supabase/.env`

**Change**:
```bash
# Before
MAILER_AUTOCONFIRM=false

# After
MAILER_AUTOCONFIRM=true
```

**Action**: Restarted auth service
```bash
docker compose restart auth
# Status: Up 10 seconds (healthy) ✅
```

### 2. Frontend Supabase Configuration Created

**File**: `frontend/.env.local` (NEW)

```env
# Supabase API URL (Kong gateway)
NEXT_PUBLIC_SUPABASE_URL=http://localhost:18000

# Supabase Anon Key
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...

# Service Role Key (for E2E)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# E2E Test Credentials
E2E_TEST_EMAIL=e2e-test@pilotspace.dev
E2E_TEST_PASSWORD=TestPassword123!
```

### 3. Old Auth State Deleted

**File**: `frontend/e2e/.auth/user.json`

**Action**: Deleted empty auth state to force recreation

---

## ✅ Supabase Status

### Docker Containers Running

```
✅ pilot-space-auth      (healthy)    - GoTrue auth service
✅ pilot-space-db        (healthy)    - PostgreSQL 15.8 on port 15432
✅ pilot-space-kong      (healthy)    - API Gateway on port 18000
✅ pilot-space-redis     (healthy)    - Redis on port 6379
✅ pilot-space-studio    (running)    - Studio on port 54323
✅ pilot-space-rest      (healthy)    - PostgREST
✅ pilot-space-storage   (running)    - Storage API
✅ pilot-space-realtime  (running)    - Realtime
⚠️ pilot-space-functions (unhealthy)  - Edge Functions
⚠️ pilot-space-meilisearch (unhealthy) - Search
```

### Key Services Status

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **Kong Gateway** | 18000 | ✅ Healthy | API Gateway (single entry point) |
| **Auth (GoTrue)** | N/A | ✅ Healthy | Authentication service |
| **Database** | 15432 | ✅ Healthy | PostgreSQL |
| **Redis** | 6379 | ✅ Healthy | Cache & sessions |
| **Studio** | 54323 | ⚠️ Running | Supabase Dashboard |

---

## ⚠️ Current Issue: Auth State Still Empty

### Test Output

```
✅ Global setup: Created and logged in test user
```

**But**: Auth state file remains empty
```json
{
  "cookies": [],
  "origins": []
}
```

### Root Cause Analysis

**Hypothesis 1: Frontend Not Using .env.local in Tests**
- Next.js may not load `.env.local` during Playwright tests
- Tests might be using default/production Supabase URL
- Need to verify environment variable loading

**Hypothesis 2: Supabase Using localStorage, Not Cookies**
- Supabase stores auth tokens in localStorage
- Playwright's `context.storageState()` should capture this
- But it might not be saved correctly if the URL is wrong

**Hypothesis 3: CORS or API Gateway Issue**
- Frontend might not be able to reach `http://localhost:18000`
- CORS headers might block the auth flow
- Need to check Kong configuration

---

## 🔍 Diagnostic Steps Performed

### 1. Check Supabase Keys ✅

```bash
grep -E "(ANON_KEY|SERVICE_ROLE_KEY)" infra/supabase/.env
# ✅ Keys found and configured
```

### 2. Check Email Confirmation ✅

```bash
grep "MAILER_AUTOCONFIRM" infra/supabase/.env
# ✅ Now set to true
```

### 3. Restart Auth Service ✅

```bash
docker compose restart auth
# ✅ Restarted successfully, healthy
```

### 4. Check Auth Endpoint ✅

```bash
curl http://localhost:18000/auth/v1/health
# ✅ Responds (requires API key)
```

### 5. Run E2E Test ✅

```bash
pnpm test:e2e:headed --project=chromium --grep="login"
# ✅ Test runs (not redirecting to login)
# ⚠️ Fails on accessibility violations (expected)
```

---

## 🎯 Recommended Next Steps

### Option 1: Verify Environment Variables in Tests

**Check if .env.local is loaded**:

Add debug logging to `e2e/global-setup.ts`:

```typescript
export default async function globalSetup(config: FullConfig): Promise<void> {
  console.log('🔍 Supabase URL:', process.env.NEXT_PUBLIC_SUPABASE_URL);
  console.log('🔍 Anon Key:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.substring(0, 20) + '...');

  // Rest of setup...
}
```

**Run test and check output**:
```bash
pnpm test:e2e:headed --grep="login" 2>&1 | grep "Supabase URL"
```

**Expected**: Should see `http://localhost:18000`
**If different**: Environment not loaded, need to fix

---

### Option 2: Use Playwright Env Configuration

**Update `playwright.config.ts`**:

```typescript
export default defineConfig({
  // ... existing config ...

  use: {
    baseURL: 'http://localhost:3000',
    // Add environment variables for Playwright
    extraHTTPHeaders: {
      'x-supabase-url': 'http://localhost:18000',
    },
  },

  // Set environment variables for webServer
  webServer: [
    {
      command: 'cd ../backend && uv run uvicorn pilot_space.main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: 'NEXT_PUBLIC_SUPABASE_URL=http://localhost:18000 NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci... pnpm dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      env: {
        NEXT_PUBLIC_SUPABASE_URL: 'http://localhost:18000',
        NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
      },
    },
  ],
});
```

---

### Option 3: Create Test User Programmatically

**Use Supabase Admin API directly in global-setup.ts**:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseAdmin = createClient(
  'http://localhost:18000',
  'eyJhbGci...SERVICE_ROLE_KEY...',
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  }
);

// Create test user with admin API (bypasses email)
const { data: user, error } = await supabaseAdmin.auth.admin.createUser({
  email: TEST_USER.email,
  password: TEST_USER.password,
  email_confirm: true,
});

// Then use anon client to login as that user
const supabaseAnon = createClient(
  'http://localhost:18000',
  'eyJhbGci...ANON_KEY...'
);

const { data: session } = await supabaseAnon.auth.signInWithPassword({
  email: TEST_USER.email,
  password: TEST_USER.password,
});

// Manually save session to storage state
if (session) {
  await context.addCookies([
    {
      name: 'sb-access-token',
      value: session.session.access_token,
      domain: 'localhost',
      path: '/',
    },
  ]);
}
```

---

### Option 4: Use Backend Test Mode (Simplest)

**Skip Supabase entirely for E2E tests**:

Add test bypass token in backend:

```python
# backend/src/pilot_space/infrastructure/auth/__init__.py

async def verify_token(token: str) -> TokenPayload:
    # E2E test bypass
    if os.getenv("TESTING") == "true" and token.startswith("test-"):
        return TokenPayload(
            sub="test-user-id-12345",
            email="e2e-test@pilotspace.dev",
            role="authenticated",
            # ... other required fields
        )

    # Normal Supabase verification
    return await verify_supabase_token(token)
```

**In global-setup.ts**:

```typescript
// Just set a test token, no Supabase needed
await context.addCookies([
  {
    name: 'Authorization',
    value: 'Bearer test-bypass-token-12345',
    domain: 'localhost',
    path: '/',
  },
]);
```

**Pros**: Fast, no external dependencies
**Cons**: Not testing real auth flow

---

## 📊 Current Test Status

### Tests Running ✅

- Backend webServer: ✅ Started on port 8000
- Frontend webServer: ✅ Started on port 3000
- Supabase services: ✅ Healthy and accessible
- Playwright: ✅ 10 workers configured
- Global setup: ✅ Executes without errors

### Tests Passing ❌

- Auth state: ❌ Still empty
- Authenticated flows: ❌ Not tested yet
- Accessibility tests: ⚠️ Running but failing on violations (expected)

---

## 🎯 Immediate Action Required

**Choose one option and implement**:

1. **Option 1** (5 min): Add debug logging, verify environment loading
2. **Option 2** (15 min): Explicitly pass env vars in Playwright config
3. **Option 3** (30 min): Use Supabase Admin API in global-setup
4. **Option 4** (1 hour): Implement backend test mode

**Recommended**: **Option 3** (Supabase Admin API) - Most reliable, tests real auth

---

## 📝 Summary

### ✅ Progress Made

1. Supabase Docker containers running and healthy
2. MAILER_AUTOCONFIRM enabled (no email confirmation)
3. Frontend .env.local created with correct keys
4. Auth service restarted with new config
5. Old auth state deleted
6. Tests running (not redirecting to login)

### ⚠️ Remaining Issue

Auth state file still empty after global setup, despite success message.

**Likely Cause**: Frontend not connecting to local Supabase (localhost:18000) during tests

**Solution**: Implement Option 3 (Supabase Admin API) to create user and session programmatically

---

## 📄 Files Modified

1. ✅ `infra/supabase/.env` - MAILER_AUTOCONFIRM=true
2. ✅ `frontend/.env.local` - Created with Supabase keys
3. ✅ `frontend/e2e/.auth/user.json` - Deleted (will be recreated)
4. ✅ Supabase auth service - Restarted

---

**Document Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: Supabase Configured, Auth State Issue Remains
**Next Action**: Implement Option 3 (Supabase Admin API) for reliable auth
