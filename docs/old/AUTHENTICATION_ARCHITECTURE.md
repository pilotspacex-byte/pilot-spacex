# Authentication Feature - Comprehensive Architecture Documentation

## Overview

The Authentication subsystem in Plane supports multiple authentication methods including email/password, magic link codes, and OAuth providers (Google, GitHub, GitLab, Gitea). The system uses an adapter pattern for extensibility and integrates with Django's session-based authentication.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Adapters & Providers](#adapters--providers)
4. [Session Management](#session-management)
5. [Frontend Architecture](#frontend-architecture)
6. [Security Considerations](#security-considerations)

---

## Data Models

### User Model

**File**: `apps/api/plane/db/models/user.py`

#### Core Identity Fields
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUIDField (PK) | Unique identifier |
| `email` | CharField (unique) | Primary authentication credential |
| `username` | CharField (unique) | System identification |
| `display_name` | CharField | Public-facing name |
| `first_name`, `last_name` | CharField | Profile information |

#### Authentication State
| Field | Type | Purpose |
|-------|------|---------|
| `is_password_autoset` | BooleanField | Password auto-generated (OAuth/magic link) |
| `is_email_verified` | BooleanField | Email verification status |
| `is_active` | BooleanField | Account active status |
| `is_password_expired` | BooleanField | Password expiration flag |
| `is_password_reset_required` | BooleanField | Force password reset |

#### Session & Activity Tracking
| Field | Type | Purpose |
|-------|------|---------|
| `token` | CharField(64) | Random session token |
| `last_active` | DateTimeField | Last activity timestamp |
| `last_login_time` | DateTimeField | Last successful login |
| `last_login_ip` | CharField(255) | Client IP of last login |
| `last_login_medium` | CharField | Authentication method used |
| `last_login_uagent` | TextField | User-Agent header |

### Account Model (OAuth Token Storage)

**File**: `apps/api/plane/db/models/user.py`

| Field | Type | Purpose |
|-------|------|---------|
| `user` | ForeignKey(User) | Account owner |
| `provider` | CharField | OAuth provider (google, github, gitlab) |
| `provider_account_id` | CharField | Provider's unique identifier |
| `access_token` | TextField | OAuth access token |
| `access_token_expired_at` | DateTimeField | Token expiration |
| `refresh_token` | TextField | OAuth refresh token |
| `id_token` | TextField | OpenID Connect ID token |

### Profile Model

| Field | Purpose |
|-------|---------|
| `user` | OneToOneField to User |
| `theme` | JSONField for UI preferences |
| `onboarding_step` | JSONField tracking progress |
| `is_onboarded` | Onboarding completion status |
| `last_workspace_id` | Last active workspace |
| `language` | Language code (default: "en") |

---

## API Endpoints

### Email Authentication

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/sign-in/` | Email/password sign in |
| POST | `/auth/sign-up/` | Email/password sign up |
| POST | `/auth/email-check/` | Check if email exists, determine auth method |

### Magic Link Authentication

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/magic-generate/` | Generate 6-digit magic code |
| POST | `/auth/magic-sign-in/` | Sign in with magic code |
| POST | `/auth/magic-sign-up/` | Sign up with magic code |

### OAuth Flows

| Provider | Initiate | Callback |
|----------|----------|----------|
| Google | `GET /auth/google/` | `GET /auth/google/callback/` |
| GitHub | `GET /auth/github/` | `GET /auth/github/callback/` |
| GitLab | `GET /auth/gitlab/` | `GET /auth/gitlab/callback/` |
| Gitea | `GET /auth/gitea/` | `GET /auth/gitea/callback/` |

### Password Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/forgot-password/` | Initiate password reset |
| GET | `/auth/reset-password/{uidb64}/{token}/` | Reset form view |
| POST | `/auth/change-password/` | Change existing password |
| POST | `/auth/set-password/` | Set auto-generated password |
| GET | `/auth/get-csrf-token/` | Get CSRF token |

---

## Adapters & Providers

### Adapter Pattern

```
Adapter (base.py)
  ├── CredentialAdapter (credential.py)
  │   └── EmailProvider
  │   └── MagicCodeProvider
  └── OauthAdapter (oauth.py)
      ├── GoogleOAuthProvider
      ├── GitHubOAuthProvider
      ├── GitLabOAuthProvider
      └── GiteaOAuthProvider
```

### Base Adapter

**File**: `apps/api/plane/authentication/adapter/base.py`

| Method | Purpose |
|--------|---------|
| `sanitize_email(email)` | Validate and normalize email |
| `validate_password(email)` | Check password strength (zxcvbn) |
| `save_user_data(user)` | Update last_login fields |
| `sync_user_data(user)` | Sync profile from provider |
| `download_and_upload_avatar()` | Fetch avatar, upload to S3 |
| `complete_login_or_signup()` | Main orchestration method |

### Email Provider

**File**: `apps/api/plane/authentication/provider/credentials/email.py`

**Sign-Up Flow**:
1. Check if ENABLE_EMAIL_PASSWORD is enabled
2. Verify user doesn't already exist
3. Validate password strength (zxcvbn score ≥ 3)
4. Hash password using Django's `set_password()`
5. Create User and Profile records

**Sign-In Flow**:
1. Look up user by email
2. Call `user.check_password(password)`
3. Set user_data if valid

### Magic Code Provider

**File**: `apps/api/plane/authentication/provider/credentials/magic_code.py`

**Token Generation**:
```python
token = secrets.randbelow(900000) + 100000  # 100000-999999
key = f"magic_{email}"

# Store in Redis with 10-minute expiry
redis.set(key, json.dumps({
    "current_attempt": attempt_count,
    "email": email,
    "token": token
}), ex=600)
```

**Rate Limiting**:
- Max attempts: 2 per 10 minutes
- After 3rd attempt: Raises EMAIL_CODE_ATTEMPT_EXHAUSTED error

### OAuth Adapter

**File**: `apps/api/plane/authentication/adapter/oauth.py`

**Token Exchange**:
```python
def get_user_token(data, headers=None):
    response = requests.post(token_url, data=data, headers=headers)
    return response.json()
```

**Account Creation/Update**:
```python
account = Account.objects.filter(
    user=user,
    provider=provider,
    provider_account_id=provider_id
).first()

if account:
    account.access_token = new_token
    account.save()
else:
    Account.objects.create(...)
```

### OAuth Providers

| Provider | Scope | Key Features |
|----------|-------|--------------|
| Google | `userinfo.email userinfo.profile` | Standard OAuth 2.0 |
| GitHub | `read:user user:email` + `read:org` | Org membership validation |
| GitLab | `read_user` | Self-hosted support via GITLAB_HOST |
| Gitea | Similar to GitLab | Self-hosted support |

---

## Session Management

### Session Middleware

**File**: `apps/api/plane/authentication/middleware/session.py`

```python
process_request(request):
    if "instances" in request.path:
        session_key = COOKIES[ADMIN_SESSION_COOKIE_NAME]
    else:
        session_key = COOKIES[SESSION_COOKIE_NAME]
    request.session = SessionStore(session_key)
```

### User Login Function

**File**: `apps/api/plane/authentication/utils/login.py`

```python
def user_login(request, user, is_app=False, is_admin=False):
    login(request=request, user=user)

    if is_admin:
        request.session.set_expiry(ADMIN_SESSION_COOKIE_AGE)

    device_info = {
        "user_agent": request.META.get("HTTP_USER_AGENT"),
        "ip_address": get_client_ip(request),
        "domain": base_host(request)
    }

    request.session["device_info"] = device_info
    request.session.save()
```

---

## Frontend Architecture

### Auth Service

**File**: `apps/web/core/services/auth.service.ts`

```typescript
class AuthService extends APIService {
  requestCSRFToken(): Promise<ICsrfTokenData>
  emailCheck(data: IEmailCheckData): Promise<IEmailCheckResponse>
  sendResetPasswordLink(data: { email: string }): Promise<any>
  setPassword(token: string, data: { password: string }): Promise<any>
  generateUniqueCode(data: { email: string }): Promise<any>
  signOut(baseUrl: string): Promise<any>
}
```

### Profile Store (MobX)

**File**: `apps/web/core/store/user/profile.store.ts`

```typescript
interface IUserProfileStore {
  isLoading: boolean
  data: TUserProfile

  fetchUserProfile(): Promise<TUserProfile | undefined>
  updateUserProfile(data: Partial<TUserProfile>): Promise<TUserProfile | undefined>
  finishUserOnboarding(): Promise<void>
  updateUserTheme(data: Partial<IUserTheme>): Promise<TUserProfile | undefined>
}
```

### User Service

**File**: `apps/web/core/services/user.service.ts`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `currentUser()` | GET `/api/users/me/` | Fetch current user |
| `getCurrentUserProfile()` | GET `/api/users/me/profile/` | Fetch profile |
| `updateCurrentUserProfile()` | PATCH `/api/users/me/profile/` | Update profile |
| `getCurrentUserAccounts()` | GET `/api/users/me/accounts/` | Fetch OAuth accounts |
| `changePassword()` | POST `/auth/change-password/` | Change password |

---

## Security Considerations

### Password Security

| Component | Measure |
|-----------|---------|
| Hashing | Django's PBKDF2 with SHA256 |
| Strength | zxcvbn validation (score ≥ 3) |
| Reset | Token-based with time expiry |
| Autoset | Flag distinguishes OAuth/magic from user-set |

### Session Security

| Component | Measure |
|-----------|---------|
| Cookies | HttpOnly, Secure flags |
| SameSite | Configured for CSRF prevention |
| Expiry | Separate ages for admin/app |
| Device Tracking | User-Agent and IP stored |

### OAuth Security

| Component | Measure |
|-----------|---------|
| State Parameter | UUID4 generated per initiate |
| CSRF | State validated on callback |
| Tokens | Stored in Account model |
| Expiry Tracking | Both access and refresh token expiry stored |
| Org Validation | GitHub supports org membership enforcement |

### Rate Limiting

```python
class AuthenticationThrottle(AnonRateThrottle):
    rate = "30/minute"
    scope = "authentication"
```

Applies to: Magic code generation, email check, all auth endpoints

---

## Error Codes

| Category | Error Code | HTTP | Meaning |
|----------|-----------|------|---------|
| Global | INSTANCE_NOT_CONFIGURED | 5000 | Server not initialized |
| | INVALID_EMAIL | 5005 | Email format invalid |
| | SIGNUP_DISABLED | 5015 | Sign-up closed |
| Password | INVALID_PASSWORD | 5020 | Password too weak |
| Sign-Up | USER_ALREADY_EXIST | 5030 | Email registered |
| Sign-In | USER_DOES_NOT_EXIST | 5060 | User not found |
| | AUTHENTICATION_FAILED_SIGN_IN | 5065 | Wrong password |
| Magic | INVALID_MAGIC_CODE_SIGN_IN | 5090 | Wrong code |
| | EXPIRED_MAGIC_CODE_SIGN_IN | 5095 | Code expired |
| | EMAIL_CODE_ATTEMPT_EXHAUSTED | 5100 | Too many attempts |
| OAuth | GOOGLE_NOT_CONFIGURED | 5105 | Missing credentials |
| | GITHUB_USER_NOT_IN_ORG | 5122 | Org membership required |

---

## Data Flow Diagrams

### OAuth Flow

```
User clicks "Sign in with Google"
    ↓
GoogleOauthInitiateEndpoint
    ├─ Generate state token (CSRF)
    └─ Store in session
    ↓
Redirect to Google OAuth URL
    ↓
(User authorizes)
    ↓
Google redirects to /auth/google/callback/
    ↓
GoogleCallbackEndpoint
    ├─ Validate state matches session
    ├─ Exchange code for tokens
    ├─ Fetch user info
    ├─ Download avatar, upload to S3
    ├─ Create/update User & Account
    └─ user_login()
    ↓
Redirect to dashboard
```

### Magic Link Flow

```
User Email Input
    ↓
MagicGenerateEndpoint
    ├─ MagicCodeProvider.initiate()
    ├─ Generate 6-digit code
    └─ Store in Redis (10-min expiry)
    ↓
Celery Task: Send email with code
    ↓
(User enters code)
    ↓
MagicSignInEndpoint
    ├─ Verify code from Redis
    ├─ Create/update User (is_password_autoset=True)
    └─ user_login()
    ↓
Redirect to dashboard
```

---

## Configuration

### Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `ENABLE_SIGNUP` | Allow new user registration |
| `ENABLE_EMAIL_PASSWORD` | Email/password authentication |
| `ENABLE_MAGIC_LINK_LOGIN` | Magic link auth |
| `EMAIL_HOST` | SMTP server |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GITHUB_CLIENT_ID` | GitHub OAuth |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth |
| `GITHUB_ORGANIZATION_ID` | GitHub org filter (optional) |
| `GITLAB_CLIENT_ID` | GitLab OAuth |
| `GITLAB_CLIENT_SECRET` | GitLab OAuth |
| `GITLAB_HOST` | GitLab instance URL |

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| User Model | `apps/api/plane/db/models/user.py` |
| Base Adapter | `apps/api/plane/authentication/adapter/base.py` |
| Credential Adapter | `apps/api/plane/authentication/adapter/credential.py` |
| OAuth Adapter | `apps/api/plane/authentication/adapter/oauth.py` |
| Error Codes | `apps/api/plane/authentication/adapter/error.py` |
| Email Provider | `apps/api/plane/authentication/provider/credentials/email.py` |
| Magic Provider | `apps/api/plane/authentication/provider/credentials/magic_code.py` |
| Google Provider | `apps/api/plane/authentication/provider/oauth/google.py` |
| GitHub Provider | `apps/api/plane/authentication/provider/oauth/github.py` |
| GitLab Provider | `apps/api/plane/authentication/provider/oauth/gitlab.py` |
| Session Middleware | `apps/api/plane/authentication/middleware/session.py` |
| Login Utility | `apps/api/plane/authentication/utils/login.py` |
| Rate Limiter | `apps/api/plane/authentication/rate_limit.py` |
| Auth Service | `apps/web/core/services/auth.service.ts` |
| User Service | `apps/web/core/services/user.service.ts` |
| Profile Store | `apps/web/core/store/user/profile.store.ts` |
