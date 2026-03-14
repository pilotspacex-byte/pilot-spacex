# Pilot Space — Free-Tier Deployment Guide

Deploy Pilot Space to production using **$0/month** free-tier services.

## Architecture Overview

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Vercel         │────▶│   Render          │────▶│   Supabase Cloud    │
│   (Frontend)     │     │   (Backend API)   │     │   (DB + Auth + RLS) │
│   Next.js SSR    │     │   FastAPI Docker  │     │   PostgreSQL        │
│   Port 3000      │     │   Port 8000       │     │   Port 5432         │
└─────────────────┘     └──────┬───────────┘     └─────────────────────┘
                               │
                        ┌──────┴───────────┐
                        │   Upstash Redis   │
                        │   (Cache/Queues)  │
                        │   REST API        │
                        └──────────────────┘
```

## Free Tier Summary

| Service          | Role                | Free Tier Limits (as of March 2026)                          | Pricing Page                                              |
|------------------|---------------------|--------------------------------------------------------------|-----------------------------------------------------------|
| **Vercel**       | Frontend hosting    | 4 CPU-hrs, 360 GB-hrs memory, 1M invocations, 50K analytics | [vercel.com/pricing](https://vercel.com/pricing)          |
| **Render**       | Backend API         | 750h/month, spins down after 15min idle                      | [render.com/pricing](https://render.com/pricing)          |
| **Supabase**     | DB + Auth + Storage | 500MB DB, 1GB storage, 50K MAU, 500K edge invocations       | [supabase.com/pricing](https://supabase.com/pricing)      |
| **Upstash**      | Redis / Queues      | 500K commands/month, 256MB, 1 free database                 | [upstash.com/pricing](https://upstash.com/docs/redis/overall/pricing) |

> **Cold start warning**: Render free tier sleeps after 15 min of inactivity. First request after sleep takes ~30s. Supabase free projects pause after 7 days of inactivity.

---

## Prerequisites

- GitHub account (repo must be on GitHub)
- [Vercel account](https://vercel.com/signup) (sign up with GitHub)
- [Render account](https://render.com/register) (sign up with GitHub)
- [Supabase account](https://supabase.com/dashboard) (sign up with GitHub)
- [Upstash account](https://console.upstash.com) (sign up with GitHub)

---

## Step 1: Supabase Cloud (Database + Auth)

Supabase replaces your local `infra/supabase` Docker stack.

### 1.1 Create Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Click **New Project**
3. Fill in:
   - **Name**: `pilot-space`
   - **Database Password**: Generate a strong password → **save it**
   - **Region**: Choose closest to your users
4. Click **Create new project** → wait ~2 min for provisioning

### 1.2 Collect Credentials

From **Project Settings → API**:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=eyJ...         # public anon key
SUPABASE_SERVICE_ROLE_KEY=eyJ... # service role key (backend only, NEVER expose to frontend)
```

From **Project Settings → Database**:

```env
# Connection string (Transaction mode for serverless)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

> Use the **connection pooler** URL (port 6543) with `?pgbouncer=true` for serverless. Use direct connection (port 5432) for migrations only.

### 1.3 Run Migrations

From your local machine, point Alembic at the cloud database:

```bash
cd backend

# Set the cloud database URL (direct connection for migrations)
export DATABASE_URL="postgresql://postgres.[project-ref]:[password]@db.[project-ref].supabase.co:5432/postgres"

# Run all migrations
uv run alembic upgrade head
```

### 1.4 Configure Auth

From **Authentication → Providers**:

1. Enable **Email** provider (enabled by default)
2. Configure **Site URL**: `https://your-app.vercel.app`
3. Add **Redirect URLs**:
   - `https://your-app.vercel.app/**`
   - `http://localhost:3000/**` (for local dev)

### 1.5 Enable Required Extensions

From **Database → Extensions**, enable:

- `pgvector` — vector embeddings for AI memory
- `pg_cron` — scheduled jobs (if used)

### 1.6 Apply RLS Policies

If your Alembic migrations include RLS policies, they should already be applied. Verify in **Database → Policies** that tables have appropriate policies.

---

## Step 2: Upstash Redis

### 2.1 Create Database

1. Go to [console.upstash.com](https://console.upstash.com)
2. Click **Create Database**
3. Fill in:
   - **Name**: `pilot-space`
   - **Region**: Same region as Supabase
   - **TLS**: Enabled (default)
4. Click **Create**

### 2.2 Collect Credentials

From the database details page:

```env
REDIS_URL=rediss://default:<password>@<endpoint>.upstash.io:6379
```

> Note: `rediss://` (with double `s`) = TLS-encrypted connection.

---

## Step 3: Render (Backend API)

### 3.1 Create Web Service

1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `pilot-space-api`
   - **Region**: Same region as Supabase
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - **Instance Type**: `Free`

### 3.2 Environment Variables

Add these in **Environment → Environment Variables**:

```env
# Application
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000

# Database (use pooler URL)
DATABASE_URL=postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true

# Supabase Auth
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=<from Supabase Settings → API → JWT Secret>

# Redis
REDIS_URL=rediss://default:<password>@<endpoint>.upstash.io:6379

# AI Provider Keys (BYOK - add whichever you use)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# CORS - allow your Vercel frontend
CORS_ORIGINS=["https://your-app.vercel.app"]
```

### 3.3 Deploy

Click **Create Web Service**. Render will:
1. Clone your repo
2. Build the Docker image from `backend/Dockerfile`
3. Start the container on port 8000

Your API will be available at: `https://pilot-space-api.onrender.com`

### 3.4 Verify

```bash
curl https://pilot-space-api.onrender.com/health
# Expected: {"status": "healthy"}
```

---

## Step 4: Vercel (Frontend)

### 4.1 Import Project

1. Go to [vercel.com/new](https://vercel.com/new)
2. **Import** your GitHub repo
3. Configure:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `pnpm build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)
   - **Install Command**: `pnpm install`

### 4.2 Environment Variables

Add in **Settings → Environment Variables**:

```env
# Backend API URL (Render service URL)
BACKEND_URL=https://pilot-space-api.onrender.com

# Supabase (public keys only - these are safe for the browser)
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Y-WebSocket (if deploying collaborative editing)
NEXT_PUBLIC_YJS_WEBSOCKET_URL=wss://your-yjs-server.example.com
```

### 4.3 Configure Build

Vercel auto-detects `output: 'standalone'` from `next.config.ts`. No extra config needed.

> **Important**: The `rewrites` in `next.config.ts` proxy `/api/v1/*` to `BACKEND_URL`. This avoids CORS issues since the browser only talks to Vercel's domain.

### 4.4 Deploy

Click **Deploy**. Vercel will:
1. Install dependencies with `pnpm install`
2. Build the Next.js app
3. Deploy to the edge network

Your app will be available at: `https://your-app.vercel.app`

### 4.5 Custom Domain (Optional)

1. Go to **Settings → Domains**
2. Add your domain (e.g., `app.pilotspace.dev`)
3. Update DNS records as instructed
4. Update Supabase **Site URL** and **Redirect URLs** to match

---

## Step 5: Post-Deployment Verification

### 5.1 Health Checks

```bash
# Backend health
curl https://pilot-space-api.onrender.com/health

# Frontend health (via API proxy)
curl https://your-app.vercel.app/api/v1/health

# Supabase connectivity (from backend logs in Render dashboard)
# Check Render → Logs for any database connection errors
```

### 5.2 Auth Flow Test

1. Open `https://your-app.vercel.app`
2. Click **Sign Up** → create a test account
3. Check email for confirmation (Supabase sends it)
4. Log in → verify workspace loads

### 5.3 API Proxy Test

```bash
# This should proxy through Vercel to Render backend
curl https://your-app.vercel.app/api/v1/health
```

---

## Step 6: Y-WebSocket Server (Optional)

The collaborative editor requires a Y-WebSocket server. Options:

### Option A: Render (Free)

1. Create another **Web Service** on Render
2. **Root Directory**: `docker/y-websocket`
3. **Runtime**: Docker
4. **Instance Type**: Free
5. Add env var: `PORT=1234`

The WebSocket URL will be: `wss://pilot-space-yjs.onrender.com`

### Option B: Skip It

If you don't need real-time collaborative editing yet, skip this. The editor works in single-user mode without it.

---

## Environment Variables Reference

### Backend (Render)

| Variable                   | Required | Description                          |
|----------------------------|----------|--------------------------------------|
| `DATABASE_URL`             | Yes      | PostgreSQL connection (pooler URL)   |
| `SUPABASE_URL`             | Yes      | Supabase project URL                 |
| `SUPABASE_ANON_KEY`        | Yes      | Supabase public anon key             |
| `SUPABASE_SERVICE_ROLE_KEY`| Yes      | Supabase service role key            |
| `SUPABASE_JWT_SECRET`      | Yes      | JWT verification secret              |
| `REDIS_URL`                | Yes      | Upstash Redis URL (TLS)              |
| `CORS_ORIGINS`             | Yes      | JSON array of allowed origins        |
| `ANTHROPIC_API_KEY`        | No       | For Claude AI features (BYOK)        |
| `OPENAI_API_KEY`           | No       | For OpenAI features (BYOK)           |
| `APP_ENV`                  | No       | `production` (default)               |

### Frontend (Vercel)

| Variable                          | Required | Description                     |
|-----------------------------------|----------|---------------------------------|
| `BACKEND_URL`                     | Yes      | Render backend URL              |
| `NEXT_PUBLIC_SUPABASE_URL`        | Yes      | Supabase project URL            |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`   | Yes      | Supabase public anon key        |
| `NEXT_PUBLIC_YJS_WEBSOCKET_URL`   | No       | Y-WebSocket server URL          |

---

## Troubleshooting

### Backend won't start on Render

- Check **Logs** in Render dashboard for error details
- Verify `DATABASE_URL` uses `postgresql+asyncpg://` prefix (not `postgresql://`)
- Ensure Supabase project is not paused (free tier pauses after 7 days)

### Frontend build fails on Vercel

- Ensure **Root Directory** is set to `frontend`
- Check that `pnpm-lock.yaml` is committed
- Verify env vars are set for the correct environment (Production/Preview)

### CORS errors

- Verify `CORS_ORIGINS` on Render includes your Vercel domain
- The Next.js rewrite proxy (`/api/v1/*`) should eliminate most CORS issues
- Check browser DevTools → Network tab for the actual origin being blocked

### Auth redirects fail

- Update Supabase **Site URL** to your Vercel domain
- Add Vercel domain to **Redirect URLs** in Supabase Auth settings
- Ensure `NEXT_PUBLIC_SUPABASE_URL` matches the project URL exactly

### Database connection timeout

- Use the **connection pooler** URL (port 6543), not direct (port 5432)
- Add `?pgbouncer=true` to the connection string
- Check if Supabase project is paused → resume it from dashboard

### Render cold starts (30s delay)

This is a limitation of the free tier. Options:
- Use [UptimeRobot](https://uptimerobot.com) (free) to ping your backend every 14 min
- Upgrade to Render Starter ($7/month) for always-on

---

## Cost Scaling Guide

When you outgrow free tiers:

| Need                        | Upgrade To                        | Cost        |
|-----------------------------|-----------------------------------|-------------|
| No cold starts              | Render Starter                    | $7/month    |
| More DB storage             | Supabase Pro                      | $25/month   |
| More Redis commands          | Upstash Pay-as-you-go             | ~$1-5/month |
| Custom domain + analytics   | Vercel Pro                        | $20/month   |
| **Recommended starter**     | Render + Supabase Pro             | ~$32/month  |
