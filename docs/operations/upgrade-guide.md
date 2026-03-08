# Zero-Downtime Upgrade Guide

## Overview

This guide covers upgrading Pilot Space from the prior MVP release to the enterprise
release. The strategy is an **additive rolling upgrade**:

1. New schema migrations run while old code is still serving traffic (forward-compatible
   columns are nullable or carry defaults, so old code ignores them).
2. New application code is deployed via a Kubernetes rolling restart — old pods drain
   naturally while new pods pass the readiness probe (`/health/ready`).

Total downtime: **zero** (assuming Kubernetes readiness/liveness probes are configured
and a minimum of 2 replicas are running).

---

## Prerequisites

| Requirement | How to verify |
|-------------|--------------|
| `kubectl` access to cluster | `kubectl get nodes` |
| Helm 3.x installed | `helm version` |
| `pilot` CLI authenticated | `pilot backup create --help` |
| `pg_dump` on PATH | `pg_dump --version` |
| At least 2 backend replicas running | `kubectl get deployment pilot-space-backend -n pilot-space` |
| Pre-upgrade backup passphrase ready | Store in secrets manager before starting |

> If you have not authenticated the CLI yet, run `pilot login` and follow the prompts.

---

## Step-by-Step Upgrade

### Step 1: Create a Pre-Upgrade Backup

Create an encrypted backup before touching any code or schema.

```bash
BACKUP_PASSPHRASE="$(vault kv get -field=value secret/pilot-space/backup-passphrase)" \
  pilot backup create \
  --encrypt \
  --output ./backups/pre-upgrade
```

Verify the archive was created before continuing:

```bash
ls -lh ./backups/pre-upgrade/
# Expected: pilot-space-backup-<timestamp>.tar.gz.enc
```

Validate the archive is intact (dry run, no DB modification):

```bash
pilot backup restore \
  --dry-run \
  ./backups/pre-upgrade/pilot-space-backup-<timestamp>.tar.gz.enc
# Expected output: "Dry run complete — archive is valid"
```

> **Do not proceed** if the dry-run validation fails. See
> [docs/operations/backup-restore.md](./backup-restore.md) for troubleshooting.

---

### Step 2: Run Additive Schema Migrations

Run Alembic migrations **before** replacing application pods. Because all new columns
are nullable or carry database defaults, the old application code continues to work
correctly against the new schema.

```bash
kubectl exec -n pilot-space \
  deployment/pilot-space-backend \
  -- \
  uv run alembic upgrade head
```

Expected output ends with:

```
INFO  [alembic.runtime.migration] Running upgrade <prior_rev> -> <new_rev>, <description>
```

---

### Step 3: Verify Migrations Applied

Confirm the revision matches the expected head before deploying new code.

```bash
kubectl exec -n pilot-space \
  deployment/pilot-space-backend \
  -- \
  uv run alembic current
```

Expected: the revision printed matches the HEAD revision in `backend/alembic/versions/`.

To look up the expected head locally:

```bash
cd backend && alembic heads
```

If the current revision does not match: **stop and investigate** before deploying new
images. Do not proceed with a partial migration.

---

### Step 4: Rolling Restart with New Image

Deploy the new image via Helm. Kubernetes performs a rolling update: new pods start,
pass the readiness probe (`/health/ready`), then old pods drain and terminate.

```bash
helm upgrade pilot-space infra/helm/pilot-space/ \
  --namespace pilot-space \
  --set backend.image.tag=<NEW_VERSION> \
  --set frontend.image.tag=<NEW_VERSION> \
  --wait \
  --timeout 10m
```

Monitor the rollout in a separate terminal:

```bash
kubectl rollout status deployment/pilot-space-backend -n pilot-space
kubectl rollout status deployment/pilot-space-frontend -n pilot-space
```

Expected final line: `deployment "pilot-space-backend" successfully rolled out`

> The `--wait` flag on `helm upgrade` already blocks until rollout completes.
> The `--timeout 10m` allows up to 10 minutes for pods to become ready.

---

### Step 5: Run Cleanup Migrations (if applicable)

> Cleanup migrations drop deprecated columns or types. They are only included in
> releases explicitly marked `CLEANUP` in the migration file name (e.g.,
> `075_cleanup_deprecated_columns.py`). If the release notes do not mention a cleanup
> migration, skip this step.

After new pods are serving traffic, run cleanup migrations:

```bash
kubectl exec -n pilot-space \
  deployment/pilot-space-backend \
  -- \
  uv run alembic upgrade head
```

This is a no-op if there are no cleanup migrations.

---

### Step 6: Smoke Test

Verify the cluster is healthy after the upgrade.

**Readiness check:**

```bash
curl -sf https://<YOUR_HOST>/health/ready | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['status'])"
# Expected: healthy
```

**API check (requires a valid access token):**

```bash
curl -sf \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://<YOUR_HOST>/api/v1/workspaces?limit=1" \
  | python3 -c "import sys, json; r=json.load(sys.stdin); print('OK — workspace count:', r.get('total', '?'))"
# Expected: 200 OK
```

**Full health detail:**

```bash
curl -sf https://<YOUR_HOST>/health/ready | python3 -m json.tool
```

Expected shape:

```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok", "latency_ms": 2},
    "redis":    {"status": "ok", "latency_ms": 1},
    "supabase": {"status": "ok", "latency_ms": 10}
  }
}
```

If `status` is `degraded`, check the individual `checks` — a Supabase connectivity
blip does not stop traffic (Supabase is non-critical). If `status` is `unhealthy`,
initiate rollback immediately (see below).

---

## Schema Migration Contract

All Alembic migrations in this codebase follow these rules to maintain forward
compatibility between consecutive releases:

| Rule | Detail |
|------|--------|
| **Additive only (same release)** | New columns MUST be nullable OR carry a `server_default`. Old code must be able to write rows that omit the new column. |
| **No column drops (same release)** | Drops happen in a separate "cleanup" migration tagged `CLEANUP` in the file name, released at least one version after the column was deprecated. |
| **No column renames** | Rename = add new column → backfill → deprecate old → drop in a later release. Never rename in place. |
| **No destructive type changes (same release)** | Type widening (e.g., `VARCHAR(50)` → `VARCHAR(255)`) is safe. Type narrowing or type replacement requires the add/backfill/drop pattern. |
| **Single migration head** | Before merging a migration PR, run `alembic heads`. Must show exactly one head. |

Violations of this contract break the zero-downtime upgrade guarantee and require a
maintenance window.

---

## Rollback Procedure

If the upgrade fails at any step, initiate rollback in reverse order.

### Application rollback (Steps 4–6 failure)

Roll back both deployments to the previous image:

```bash
kubectl rollout undo deployment/pilot-space-backend -n pilot-space
kubectl rollout undo deployment/pilot-space-frontend -n pilot-space
```

Wait for rollout:

```bash
kubectl rollout status deployment/pilot-space-backend -n pilot-space
```

### Schema rollback (Step 2–3 failure)

Downgrade the migration one step at a time (each step rolls back one migration):

```bash
kubectl exec -n pilot-space deployment/pilot-space-backend \
  -- uv run alembic downgrade -1
```

Repeat until `alembic current` shows the prior release revision.

> Only downgrade if explicitly needed. Rolling back a completed migration is risky if
> rows were written against the new schema. Assess whether a forward-fix migration is
> safer.

### Full restore (catastrophic failure)

If both application and schema rollback fail, restore from the pre-upgrade backup:

```bash
pilot backup restore \
  ./backups/pre-upgrade/pilot-space-backup-<timestamp>.tar.gz.enc
# You will be prompted for the passphrase and confirmation before data is overwritten
```

See [docs/operations/backup-restore.md](./backup-restore.md) for full restore
documentation.

---

## Version Compatibility Matrix

| Enterprise Release | Upgrades From | Schema Strategy | Expected Downtime |
|-------------------|---------------|-----------------|------------------|
| v1.0 (enterprise) | MVP latest | Additive migrations only | Zero |

> Releases separated by more than one major version may require a multi-step upgrade.
> Check the release notes for intermediate migration waypoints.

---

## Automated Verification

The upgrade path is validated in CI on every push to `main` and on every pull request.
The workflow applies Alembic migrations against a fresh PostgreSQL instance, starts the
new backend, and asserts that `/health/ready` reports a healthy (or degraded) status.

See [.github/workflows/upgrade-simulation.yml](../../.github/workflows/upgrade-simulation.yml)
for the full workflow definition.

To trigger the upgrade simulation manually:

```bash
gh workflow run upgrade-simulation.yml \
  --field prior_version=mvp-latest
```
