# AuthCore

Standalone JWT authentication microservice built with FastAPI, SQLAlchemy 2.0 async, and Redis. Handles user registration, email verification, RS256-signed access/refresh tokens, account lockout, and admin role management. Designed as a drop-in auth backend for any service that needs BYOK (bring-your-own-keys) JWT auth without delegating to a third-party identity provider.

---

## Architecture

9-phase clean architecture with CQRS-lite service design:

| Layer | Contents |
|-------|----------|
| **API** | FastAPI routers + Pydantic v2 request/response schemas |
| **Application** | 12 single-responsibility service classes (`execute(Payload) → Result`) |
| **Domain** | `UserEntity`, `RefreshTokenEntity`, `PasswordPolicy`, domain exceptions |
| **Infrastructure** | SQLAlchemy 2.0 async repositories, `JWTService` (RS256), `RedisClient`, `SmtpEmailService` |
| **DI Container** | `dependency-injector` declarative container; all providers overrideable for testing |

**Token strategy**: RS256 asymmetric signing. Short-lived access tokens (15 min default) plus long-lived refresh tokens (7 days). Refresh rotation on every use with token-family theft detection — if a rotated token is reused, the entire family is revoked.

**JTI blacklist**: On logout, the access token's `jti` claim is written to Redis with a TTL matching the token's remaining lifetime. Every authenticated request checks the JTI blacklist before proceeding.

**Rate limiting**: Redis sliding window on `login_fail:{ip}:{email}`. After `LOGIN_MAX_ATTEMPTS` failures, the key is locked for `LOGIN_LOCKOUT_MINUTES`. Fails open if Redis is unavailable.

---

## Security Features

- **Token theft detection** — refresh token families; reuse of a rotated token revokes all sessions
- **JTI blacklist** — revoked access tokens blocked at the dependency level via Redis
- **Account lockout** — IP+email sliding window rate limiter on login failures
- **Email verification** — required before first login; token stored in Redis with configurable TTL
- **Silent forgot-password** — always returns 200 regardless of whether the email exists (anti-enumeration)
- **RS256 signing** — private key never leaves the service; public key can be distributed to resource servers
- **Bcrypt password hashing** — cost factor configurable at build time
- **Audit log** — every auth event (login, logout, password change, role change) written to `audit_logs` table

---

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/register` | Register new user, send verification email | — |
| `GET` | `/api/v1/auth/verify-email?token=` | Verify email address | — |
| `POST` | `/api/v1/auth/resend-verification` | Resend verification email | Bearer |
| `POST` | `/api/v1/auth/login` | Login, receive access + refresh tokens | — |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token, get new access token | — |
| `POST` | `/api/v1/auth/logout` | Revoke refresh token, blacklist JTI | Bearer |
| `POST` | `/api/v1/auth/logout-all` | Revoke all refresh tokens for user | Bearer |
| `POST` | `/api/v1/auth/change-password` | Change password, revoke all sessions | Bearer |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset email | — |
| `POST` | `/api/v1/auth/reset-password` | Reset password via token | — |
| `GET` | `/api/v1/admin/users/{id}/audit-logs` | List audit logs for a user | Bearer (admin) |
| `PUT` | `/api/v1/admin/users/{id}/role` | Change user role | Bearer (admin) |
| `GET` | `/health` | Liveness check | — |
| `GET` | `/health/ready` | Readiness check (pings Redis) | — |

---

## Quickstart with Docker

### Prerequisites

- Docker 24+ and Docker Compose v2
- `openssl` (available on macOS/Linux by default)

### 1. Generate RSA key pair

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

### 2. Configure environment

```bash
cp env.example .env
```

Open `.env` and set the two required key fields. Use the helper below to inline the PEM files:

```bash
# Inline private key (replace literal newlines with \n)
JWT_PRIVATE_KEY="$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' private.pem)"

# Inline public key
JWT_PUBLIC_KEY="$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' public.pem)"
```

Or paste the values manually into `.env`:

```dotenv
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----"
```

### 3. Start services

```bash
docker compose up -d
```

This starts PostgreSQL 16, Redis 7, and AuthCore on port 8000. Alembic migrations run automatically on startup.

### 4. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/health/ready
# {"status":"ready"}
```

### 5. Register and login

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"Secure1!"}' | jq .

# Verify email (use the token from your SMTP server or check logs)
curl -s "http://localhost:8000/api/v1/auth/verify-email?token=<TOKEN>"

# Login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"Secure1!"}' | jq .
# Returns: {"access_token":"...","refresh_token":"...","token_type":"bearer","user_id":"...","role":"member"}

# Store tokens
ACCESS=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"Secure1!"}' | jq -r .access_token)

REFRESH=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"Secure1!"}' | jq -r .refresh_token)

# Refresh token rotation
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | jq .

# Logout
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"
```

---

## Development Setup

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
cd authcore
uv venv && source .venv/bin/activate
uv sync
```

### Run tests

```bash
uv run pytest
# 171 tests, 97% coverage
```

### Quality gates

```bash
uv run pyright        # strict type checking
uv run ruff check     # linting
uv run pytest --cov=. # tests + coverage (must exceed 80%)
```

### Database migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Verify single head
alembic heads
```

---

## Configuration Reference

All settings are loaded via `pydantic-settings` from environment variables or a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL asyncpg URL: `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `JWT_PRIVATE_KEY` | *(required)* | PEM-encoded RSA private key (RS256 signing) |
| `JWT_PUBLIC_KEY` | *(required)* | PEM-encoded RSA public key (RS256 verification) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |
| `SMTP_HOST` | `localhost` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USERNAME` | `` | SMTP username (blank = unauthenticated) |
| `SMTP_PASSWORD` | `` | SMTP password |
| `SMTP_FROM_ADDRESS` | `noreply@authcore.local` | From address on outgoing emails |
| `SMTP_USE_TLS` | `true` | Enable STARTTLS |
| `APP_BASE_URL` | `http://localhost:8000` | Public base URL (used in email links) |
| `DEBUG` | `false` | Enable debug mode (open CORS, verbose errors) |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed login attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Lockout duration after exceeding attempts |
| `RESEND_VERIFICATION_MAX_PER_HOUR` | `3` | Max verification resend requests per hour |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `60` | Password reset token lifetime |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | `24` | Email verification token lifetime |

---

## Design Decisions

### RS256 instead of HS256

RS256 uses asymmetric keys — the private key signs tokens and never leaves AuthCore; the public key can be freely distributed to any resource server that needs to verify tokens without contacting AuthCore. HS256 would require sharing the secret with every resource server, creating a wider attack surface.

### Redis for JTI blacklist

Access tokens are short-lived (15 min) and stateless by design, but logout must be immediate. Writing the `jti` claim to Redis with a TTL matching the token's remaining lifetime achieves O(1) revocation checks per request without a database round-trip. If Redis is unavailable, the fail-open behavior means tokens remain valid until expiry — an acceptable trade-off for a liveness dependency.

### CQRS-lite service design

Each operation is a dedicated service class (`RegisterService`, `LoginService`, etc.) with a single `execute(Payload) → Result` method. This eliminates fat service objects, makes each operation independently testable, and keeps the router layer thin. Full CQRS with event sourcing was not adopted — the complexity is unwarranted for an auth service with well-defined, low-cardinality operations.
