# Kubernetes Deployment (Helm)

Pilot Space ships as a Helm chart at `infra/helm/pilot-space/`. The chart converts the raw manifests in `infra/k8s/` into a parameterized, production-ready deployment.

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Kubernetes cluster | 1.24+ | EKS, GKE, AKS, or self-hosted |
| Helm | 3.x | `helm version` to verify |
| kubectl | Matching cluster version | Configured for target cluster |
| cert-manager | 1.12+ | Required for automated TLS (optional if you pre-create TLS secrets) |
| NGINX Ingress Controller | 1.8+ | `helm install ingress-nginx ingress-nginx/ingress-nginx` |
| Metrics Server | 0.6+ | Required for HPA (CPU/memory autoscaling) |

**External services (managed separately):**
- PostgreSQL 15+ (AWS RDS, Google Cloud SQL, Supabase self-hosted, etc.)
- Redis 7+ (AWS ElastiCache, Upstash, etc.)
- Supabase (cloud or self-hosted via `infra/supabase/docker-compose.yml`)

## Install

### 1. Create namespace

```bash
kubectl create namespace pilot-space
```

### 2. Create secrets

All sensitive credentials are injected via Kubernetes secrets. The chart never stores credentials in `values.yaml`.

**Database secret** — must contain a full SQLAlchemy async URL:

```bash
kubectl create secret generic pilot-space-db \
  --from-literal=database-url='postgresql+asyncpg://user:password@host:5432/pilot_space' \
  -n pilot-space
```

**Redis secret** — must contain a full Redis URL:

```bash
kubectl create secret generic pilot-space-redis \
  --from-literal=redis-url='redis://:password@host:6379/0' \
  -n pilot-space
```

**Supabase secret** — three keys required:

```bash
kubectl create secret generic pilot-space-supabase \
  --from-literal=anon-key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  --from-literal=service-key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  --from-literal=jwt-secret='your-supabase-jwt-secret' \
  -n pilot-space
```

> Obtain these from your Supabase project dashboard (Settings > API) or from the `infra/supabase/.env` file for self-hosted.

### 3. Configure values

Copy and customize the values override file:

```bash
cp infra/helm/pilot-space/values.yaml values.override.yaml
```

Minimum required overrides in `values.override.yaml`:

```yaml
backend:
  image:
    repository: your-registry/pilot-space-backend
    tag: "1.2.3"

frontend:
  image:
    repository: your-registry/pilot-space-frontend
    tag: "1.2.3"

ingress:
  host: pilot-space.your-domain.com

externalDatabase:
  existingSecret: pilot-space-db       # name of secret created in step 2
  existingSecretKey: database-url

externalRedis:
  existingSecret: pilot-space-redis
  existingSecretKey: redis-url

externalSupabase:
  url: https://your-project.supabase.co
  existingSecret: pilot-space-supabase
  existingSecretAnonKey: anon-key
  existingSecretServiceKey: service-key
  existingSecretJwtSecret: jwt-secret
```

### 4. Install chart

```bash
helm install pilot-space infra/helm/pilot-space/ \
  -n pilot-space \
  -f infra/helm/pilot-space/values.production.yaml \
  -f values.override.yaml
```

For staging or development (without production resource multipliers):

```bash
helm install pilot-space infra/helm/pilot-space/ \
  -n pilot-space \
  -f values.override.yaml
```

### 5. Verify deployment

```bash
# Watch rollout
kubectl rollout status deployment/pilot-space-backend -n pilot-space
kubectl rollout status deployment/pilot-space-frontend -n pilot-space

# Check pods
kubectl get pods -n pilot-space

# Verify health endpoints
kubectl port-forward svc/pilot-space-backend 8000:8000 -n pilot-space &
curl http://localhost:8000/health/live    # {"status":"live"}
curl http://localhost:8000/health/ready  # {"status":"ready","checks":{...}}
```

## Upgrade

```bash
helm upgrade pilot-space infra/helm/pilot-space/ \
  -n pilot-space \
  -f infra/helm/pilot-space/values.production.yaml \
  -f values.override.yaml
```

Helm performs a RollingUpdate with `maxSurge: 1, maxUnavailable: 0`, ensuring zero downtime during upgrades.

To upgrade only the image tag:

```bash
helm upgrade pilot-space infra/helm/pilot-space/ \
  -n pilot-space \
  -f values.override.yaml \
  --set backend.image.tag=1.3.0 \
  --set frontend.image.tag=1.3.0
```

### Rollback

```bash
# List release history
helm history pilot-space -n pilot-space

# Rollback to previous revision
helm rollback pilot-space -n pilot-space

# Rollback to specific revision
helm rollback pilot-space 3 -n pilot-space
```

## Health Check Configuration

The backend exposes two health endpoints used by Kubernetes probes (implemented in plan 05-01 / OPS-03):

| Endpoint | Probe Type | Behavior on Failure |
|---|---|---|
| `GET /health/live` | livenessProbe | Pod is restarted |
| `GET /health/ready` | readinessProbe | Pod removed from Service endpoints (no traffic) |

**readinessProbe** (`/health/ready`): Checks database and Redis connectivity. If either dependency is down, the pod stops receiving traffic until they recover. Supabase is checked but treated as non-critical (degraded, not unhealthy).

**livenessProbe** (`/health/live`): Confirms the Python process is alive and responding. Does not check external dependencies — only process health.

**startupProbe** (`/health/live`): Gives the backend 150 seconds (30 failures × 5s period) to start before liveness/readiness probes activate. This prevents premature restarts during slow cold-starts (e.g., DB connection pool initialization).

### Adjusting probe timing

For slower environments (e.g., cold VMs, underpowered nodes):

```yaml
# values.override.yaml
backend:
  # startupProbe failureThreshold is hardcoded at 30 (150s budget)
  # Increase via custom template if needed
```

## HPA Tuning

The chart includes Horizontal Pod Autoscalers for both backend and frontend.

### Backend HPA

```yaml
autoscaling:
  backend:
    minReplicas: 2        # Floor — never scale below this
    maxReplicas: 10       # Ceiling — cost control
    targetCPUUtilizationPercentage: 70     # Scale up at 70% CPU
    targetMemoryUtilizationPercentage: 80  # Scale up at 80% memory
```

The backend uses both CPU and memory metrics because AI workloads (LLM streaming, embedding generation) can be memory-bound even at low CPU.

**Scale-up behavior:** Conservative 50% Percent or 2 Pods per 60s window — prevents thundering herd during traffic spikes.

**Scale-down behavior:** Slow 25% Percent or 1 Pod per 120s window with 300s stabilization — prevents oscillation after a spike.

### Frontend HPA

```yaml
autoscaling:
  frontend:
    minReplicas: 2
    maxReplicas: 8
    targetCPUUtilizationPercentage: 70
```

Frontend uses CPU only — Next.js standalone server has predictable memory usage.

### Disabling autoscaling

```yaml
autoscaling:
  enabled: false
```

With HPA disabled, `backend.replicaCount` and `frontend.replicaCount` control static replica counts.

## Pod Disruption Budget

PDBs prevent Kubernetes from evicting too many pods simultaneously during cluster maintenance (node drains, upgrades):

```yaml
podDisruptionBudget:
  enabled: true
  backend:
    minAvailable: 2    # At least 2 backend pods during maintenance
  frontend:
    minAvailable: 1    # At least 1 frontend pod during maintenance
```

> If you scale below `minAvailable`, `kubectl drain` will block. Always ensure `minReplicas >= minAvailable + 1` in production.

## Values Reference

| Parameter | Default | Description |
|---|---|---|
| `backend.replicaCount` | `3` | Backend pod replicas |
| `backend.image.repository` | `pilot-space/backend` | Backend image repo |
| `backend.image.tag` | `latest` | Backend image tag |
| `backend.resources.requests.cpu` | `100m` | CPU request |
| `backend.resources.limits.memory` | `512Mi` | Memory limit |
| `frontend.replicaCount` | `2` | Frontend pod replicas |
| `ingress.enabled` | `true` | Enable nginx ingress |
| `ingress.host` | `pilot-space.example.com` | Primary hostname |
| `ingress.tls.enabled` | `true` | Enable TLS |
| `externalDatabase.existingSecret` | `""` | Secret name with `database-url` key |
| `externalRedis.existingSecret` | `""` | Secret name with `redis-url` key |
| `externalSupabase.existingSecret` | `""` | Secret name with Supabase keys |
| `autoscaling.enabled` | `true` | Enable HPA |
| `podDisruptionBudget.enabled` | `true` | Enable PDB |

Full values documentation: `infra/helm/pilot-space/values.yaml` (inline comments on every parameter).

## Uninstall

```bash
helm uninstall pilot-space -n pilot-space

# Optionally delete namespace and secrets (destructive — cannot be undone)
kubectl delete namespace pilot-space
```

> Secrets created outside Helm (step 2) are not deleted by `helm uninstall`. Delete them explicitly if decommissioning.

## Troubleshooting

**Backend pods CrashLoopBackOff**

```bash
kubectl logs deployment/pilot-space-backend -n pilot-space
```

Common causes:
- `externalDatabase.existingSecret` does not exist → `kubectl get secret pilot-space-db -n pilot-space`
- Database URL format incorrect (must be `postgresql+asyncpg://`)
- Supabase JWT secret mismatch

**Pods stuck in Pending**

```bash
kubectl describe pod <pod-name> -n pilot-space
```

Common causes: insufficient cluster resources, PVC mount failures, image pull errors (check `imagePullSecrets`).

**HPA not scaling**

```bash
kubectl describe hpa pilot-space-backend-backend-hpa -n pilot-space
```

Common cause: Metrics Server not installed. Install with:

```bash
helm install metrics-server metrics-server/metrics-server -n kube-system
```
