# Phase 9: Final Polish & Production Readiness

**Epic/PR**: MVP Production Readiness - Testing, Documentation, Performance, Security
**Task Count**: 38 tasks (T323-T360)
**Combined Complexity**: 🟡 240/190 (avg 6.3/task)
**Type**: POLISH

**Scope**: Testing, documentation, performance optimization, security audit, infrastructure, accessibility, human-in-the-loop, data export/import.

---

## Shared Context

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Spec | `spec.md` | MVP requirements |
| Plan | `plan.md` | Implementation phases |
| Architecture | `docs/architect/README.md` | System design |
| Testing Standards | `docs/dev-pattern/03-testing-standards.md` | Test patterns |

## Dev Patterns (Shared)

| Pattern | File | Purpose |
|---------|------|---------|
| Testing | `docs/dev-pattern/03-testing-standards.md` | Test patterns |
| Pilot Space | `docs/dev-pattern/45-pilot-space-patterns.md` | Project overrides |
| Service Layer | `docs/dev-pattern/08-service-layer-pattern.md` | CQRS-lite |
| Component | `docs/dev-pattern/20-frontend-component-patterns.md` | UI patterns |

---

## Testing (T323-T329d)

### T323: Create backend test configuration

**Complexity**: 🟢 5/20 | **Priority**: P2 | **Story**: N/A
**Type**: SETUP

#### Objective
Create pytest configuration and fixtures for backend testing.

#### Acceptance Criteria
- [x] AC1: `backend/tests/conftest.py` with shared fixtures
- [x] AC2: Database fixture with transaction rollback
- [x] AC3: Redis mock fixture
- [x] AC4: Authenticated user fixture
- [x] AC5: Factory fixtures for common entities (User, Workspace, Project, Issue, Note)
- [x] AC6: Coverage configuration in `pyproject.toml` (>80% threshold)

#### Guidelines
```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from pilot_space.infrastructure.database import Base

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Transaction-isolated database session."""
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn)
            yield session
            await transaction.rollback()

@pytest.fixture
async def authenticated_user(db_session: AsyncSession) -> User:
    """Create test user with Supabase auth mock."""
    return await UserFactory.create(session=db_session)
```

#### Target Files
- `backend/tests/conftest.py`
- `backend/tests/factories.py`
- `backend/pyproject.toml` (coverage config)

---

### T324: Create integration tests for auth

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: TEST

#### Objective
Create integration tests for authentication flows.

#### Acceptance Criteria
- [x] AC1: Test Supabase auth callback handling
- [x] AC2: Test workspace membership verification
- [x] AC3: Test RLS policy enforcement
- [x] AC4: Test session management
- [x] AC5: Test permission checks for each role

#### Target Files
- `backend/tests/integration/test_auth.py`

---

### T325: Create integration tests for notes

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US1
**Type**: TEST

#### Objective
Create integration tests for note CRUD and AI features.

#### Acceptance Criteria
- [x] AC1: Test note CRUD operations
- [x] AC2: Test version history
- [x] AC3: Test ghost text generation (mocked AI)
- [x] AC4: Test annotation creation
- [x] AC5: Test issue extraction from note
- [x] AC6: Test RLS isolation between workspaces

#### Target Files
- `backend/tests/integration/test_notes.py`

---

### T326: Create integration tests for issues

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US2
**Type**: TEST

#### Objective
Create integration tests for issue management.

#### Acceptance Criteria
- [x] AC1: Test issue CRUD operations
- [x] AC2: Test state machine transitions
- [x] AC3: Test AI enhancement (mocked)
- [x] AC4: Test duplicate detection (mocked)
- [x] AC5: Test activity logging
- [x] AC6: Test filtering and pagination

#### Target Files
- `backend/tests/integration/test_issues.py`

---

### T327: Create frontend component tests for NoteCanvas

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: US1
**Type**: TEST

#### Objective
Create component tests for NoteCanvas and editor components.

#### Acceptance Criteria
- [x] AC1: Test NoteCanvas rendering
- [x] AC2: Test TipTap editor interactions
- [x] AC3: Test ghost text overlay
- [x] AC4: Test annotation panel
- [x] AC5: Test keyboard shortcuts
- [x] AC6: Test responsive behavior

#### Guidelines
```typescript
// Note: Use @testing-library/react with Vitest
import { render, screen, userEvent } from '@testing-library/react';
import { NoteCanvas } from './NoteCanvas';

describe('NoteCanvas', () => {
  it('renders editor with initial content', async () => {
    render(<NoteCanvas noteId="test-id" />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('shows ghost text on pause', async () => {
    // Test ghost text appearance after 500ms pause
  });
});
```

#### Target Files
- `frontend/src/components/editor/__tests__/NoteCanvas.test.tsx`

---

### T328: Create E2E tests for note workflow

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: US1
**Type**: TEST

#### Objective
Create Playwright E2E tests for note creation and editing workflow.

#### Acceptance Criteria
- [x] AC1: Test create new note flow
- [x] AC2: Test edit note with ghost text
- [x] AC3: Test accept/reject annotation
- [x] AC4: Test extract issue from note
- [x] AC5: Test version history navigation
- [x] AC6: Test pin/unpin note

#### Target Files
- `frontend/e2e/notes.spec.ts`

---

### T329: Create E2E tests for issue workflow

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: US2
**Type**: TEST

#### Objective
Create Playwright E2E tests for issue management workflow.

#### Acceptance Criteria
- [x] AC1: Test create issue with AI enhancement
- [x] AC2: Test state transitions via dropdown
- [x] AC3: Test duplicate detection alert
- [x] AC4: Test bulk operations
- [x] AC5: Test calendar view interactions
- [x] AC6: Test trash and restore

#### Target Files
- `frontend/e2e/issues.spec.ts`

---

### T329a: Create E2E tests for PR review workflow

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US3
**Type**: TEST

#### Objective
Create E2E tests for AI PR review workflow.

#### Acceptance Criteria
- [x] AC1: Test trigger PR review manually
- [x] AC2: Test review status tracking
- [x] AC3: Test review results display
- [x] AC4: Test comment navigation
- [x] AC5: Test severity filtering

#### Target Files
- `frontend/e2e/pr-review.spec.ts`

---

### T329b: Create E2E tests for cycle/sprint workflow

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US4
**Type**: TEST

#### Objective
Create E2E tests for cycle planning and velocity tracking.

#### Acceptance Criteria
- [x] AC1: Test create cycle
- [x] AC2: Test add issues to cycle
- [x] AC3: Test velocity chart display
- [x] AC4: Test burndown chart interactions
- [x] AC5: Test complete cycle flow

#### Target Files
- `frontend/e2e/cycles.spec.ts`

---

### T329c: Create E2E tests for AI context workflow

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US12
**Type**: TEST

#### Objective
Create E2E tests for AI context generation.

#### Acceptance Criteria
- [x] AC1: Test generate AI context
- [x] AC2: Test context panel display
- [x] AC3: Test copy Claude Code prompt
- [x] AC4: Test regenerate with feedback
- [x] AC5: Test context for different issue types

#### Target Files
- `frontend/e2e/ai-context.spec.ts`

---

### T329d: Create E2E tests for GitHub integration

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: US18
**Type**: TEST

#### Objective
Create E2E tests for GitHub integration flow (with mocked OAuth).

#### Acceptance Criteria
- [x] AC1: Test connect GitHub flow (mocked OAuth)
- [x] AC2: Test repository selection
- [x] AC3: Test PR link display
- [x] AC4: Test branch suggestion
- [x] AC5: Test commit list view

#### Target Files
- `frontend/e2e/github.spec.ts`

---

## Documentation (T330-T332)

### T330: Update API documentation with OpenAPI

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Ensure all API endpoints have complete OpenAPI documentation.

#### Acceptance Criteria
- [x] AC1: All endpoints have operation descriptions
- [x] AC2: Request/response schemas documented
- [x] AC3: Error responses documented (4xx, 5xx)
- [x] AC4: Authentication requirements documented
- [x] AC5: Example values for all schemas
- [x] AC6: Tags organize endpoints by feature

#### Target Files
- `backend/src/pilot_space/api/v1/routers/*.py` (docstrings)
- `backend/src/pilot_space/api/v1/schemas/*.py` (Field descriptions)

---

### T331: Create developer setup guide

**Complexity**: 🟢 5/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create comprehensive developer setup documentation.

#### Acceptance Criteria
- [x] AC1: Prerequisites section (Node, Python, Docker, etc.)
- [x] AC2: Step-by-step local setup
- [x] AC3: Environment variables documentation
- [x] AC4: Database setup and seeding
- [x] AC5: Running tests locally
- [x] AC6: Troubleshooting common issues

#### Target Files
- `docs/DEVELOPER_SETUP.md`

---

### T332: Validate quickstart.md

**Complexity**: 🟢 4/20 | **Priority**: P2 | **Story**: N/A
**Type**: TEST

#### Objective
Validate quickstart guide works on fresh environment.

#### Acceptance Criteria
- [x] AC1: Clone repo and follow quickstart
- [x] AC2: All commands execute successfully
- [x] AC3: App runs locally
- [x] AC4: Sample data loads correctly
- [x] AC5: Update any outdated steps

#### Target Files
- `docs/quickstart.md`

---

## Performance (T333-T335)

### T333: Optimize note canvas for 1000+ blocks

**Complexity**: 🟠 12/20 | **Priority**: P2 | **Story**: US1
**Type**: IMPL

#### Objective
Optimize NoteCanvas rendering for large documents.

#### Acceptance Criteria
- [x] AC1: Virtual scrolling for block list
- [x] AC2: Lazy load blocks outside viewport
- [x] AC3: Debounced autosave (500ms)
- [x] AC4: Incremental rendering on scroll
- [x] AC5: Performance budget: <100ms for initial render
- [x] AC6: Memory usage <200MB for 1000 blocks

#### Guidelines
```typescript
// Use react-window or similar for virtualization
import { VariableSizeList } from 'react-window';

function VirtualizedEditor({ blocks }: Props) {
  const getItemSize = (index: number) => estimateBlockHeight(blocks[index]);

  return (
    <VariableSizeList
      height={windowHeight}
      itemCount={blocks.length}
      itemSize={getItemSize}
      overscanCount={5}
    >
      {({ index, style }) => (
        <BlockRenderer block={blocks[index]} style={style} />
      )}
    </VariableSizeList>
  );
}
```

#### Target Files
- `frontend/src/components/editor/NoteCanvas.tsx`
- `frontend/src/components/editor/VirtualizedEditor.tsx`

---

### T334: Add Redis caching for AI responses

**Complexity**: 🟡 7/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Cache AI responses to reduce API calls and latency.

#### Acceptance Criteria
- [x] AC1: Cache ghost text suggestions (5 min TTL)
- [x] AC2: Cache issue enhancements (10 min TTL)
- [x] AC3: Cache duplicate detection results (15 min TTL)
- [x] AC4: Cache invalidation on content change
- [x] AC5: Cache key includes content hash

#### Guidelines
```python
class AICache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_or_generate(
        self,
        key_prefix: str,
        content_hash: str,
        generator: Callable[[], Awaitable[T]],
        ttl_seconds: int = 300,
    ) -> T:
        cache_key = f"{key_prefix}:{content_hash}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        result = await generator()
        await self.redis.setex(cache_key, ttl_seconds, json.dumps(result))
        return result
```

#### Target Files
- `backend/src/pilot_space/infrastructure/cache/ai_cache.py`

---

### T335: Add database query optimization

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: N/A
**Type**: REFACTOR

#### Objective
Optimize slow queries identified in development.

#### Acceptance Criteria
- [x] AC1: Add indexes for common query patterns
- [x] AC2: Optimize N+1 queries with eager loading
- [x] AC3: Add query explain analysis
- [x] AC4: Pagination optimization with cursor-based
- [x] AC5: Query response time <100ms for list views

#### Target Files
- `backend/alembic/versions/011_performance_indexes.py`
- `backend/src/pilot_space/infrastructure/database/repositories/*.py`

---

## Security (T336-T337)

### T336: Audit RLS policies

**Complexity**: 🟡 7/20 | **Priority**: P1 | **Story**: N/A
**Type**: TEST

#### Objective
Comprehensive audit of all RLS policies for security gaps.

#### Acceptance Criteria
- [x] AC1: Test cross-workspace data isolation
- [x] AC2: Test role-based access (owner, admin, editor, viewer)
- [x] AC3: Test soft-delete visibility
- [x] AC4: Test admin bypass scenarios
- [x] AC5: Document all policies with justification
- [x] AC6: No data leakage between workspaces

#### Target Files
- `backend/tests/security/test_rls_policies.py`
- `docs/security/RLS_AUDIT.md`

---

### T337: Audit rate limiting configuration

**Complexity**: 🟢 5/20 | **Priority**: P1 | **Story**: N/A
**Type**: TEST

#### Objective
Audit and test rate limiting for all endpoints.

#### Acceptance Criteria
- [x] AC1: Test standard endpoint limits (1000/min)
- [x] AC2: Test AI endpoint limits (100/min)
- [x] AC3: Test auth endpoint limits (10/min)
- [x] AC4: Test rate limit headers returned
- [x] AC5: Test graceful degradation at limit

#### Target Files
- `backend/tests/security/test_rate_limiting.py`

---

## Infrastructure (T338-T343)

### T338: Create Kubernetes manifests

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: N/A
**Type**: SETUP

#### Objective
Create Kubernetes deployment manifests for production.

#### Acceptance Criteria
- [x] AC1: Backend Deployment + Service
- [x] AC2: Frontend Deployment + Service
- [x] AC3: Ingress with TLS
- [x] AC4: ConfigMaps for environment
- [x] AC5: Secrets for credentials
- [x] AC6: HPA for autoscaling
- [x] AC7: PodDisruptionBudget

#### Target Files
- `infra/k8s/backend-deployment.yaml`
- `infra/k8s/frontend-deployment.yaml`
- `infra/k8s/ingress.yaml`

---

### T339: Create Terraform modules

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: N/A
**Type**: SETUP

#### Objective
Create Terraform modules for cloud infrastructure.

#### Acceptance Criteria
- [x] AC1: VPC module
- [x] AC2: Database module (Supabase-managed)
- [x] AC3: Redis module
- [x] AC4: Kubernetes cluster module
- [x] AC5: DNS and SSL module
- [x] AC6: Variables for multi-environment

#### Target Files
- `infra/terraform/modules/vpc/`
- `infra/terraform/modules/redis/`
- `infra/terraform/modules/k8s/`
- `infra/terraform/environments/production/`

---

### T340: Configure health check endpoints

**Complexity**: 🟢 5/20 | **Priority**: P1 | **Story**: N/A
**Type**: IMPL

#### Objective
Add health check endpoints for load balancer probes.

#### Acceptance Criteria
- [x] AC1: `/health` endpoint returns 200 if healthy
- [x] AC2: `/health/ready` checks database connection
- [x] AC3: `/health/live` basic liveness check
- [x] AC4: Include version in response
- [x] AC5: Structured JSON response

#### Guidelines
```python
@router.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "version": settings.VERSION}

@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
```

#### Target Files
- `backend/src/pilot_space/api/health.py`

---

### T341: Create environment configuration templates

**Complexity**: 🟢 5/20 | **Priority**: P2 | **Story**: N/A
**Type**: SETUP

#### Objective
Create environment variable templates and documentation.

#### Acceptance Criteria
- [x] AC1: `.env.example` with all variables
- [x] AC2: Variable descriptions in comments
- [x] AC3: Separate files for dev/staging/production
- [x] AC4: Secrets management documentation
- [x] AC5: Validation script for required variables

#### Target Files
- `backend/.env.example`
- `frontend/.env.example`
- `docs/ENV_VARIABLES.md`

---

### T342: Create backup script

**Complexity**: 🟢 5/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create database backup script for disaster recovery.

#### Acceptance Criteria
- [x] AC1: Script backs up Supabase database
- [x] AC2: Uploads to S3/GCS with timestamp
- [x] AC3: Retention policy (30 days)
- [x] AC4: Verification of backup integrity
- [x] AC5: Cron schedule documentation

#### Target Files
- `scripts/backup.sh`
- `docs/BACKUP_PROCEDURES.md`

---

### T343: Document failover procedure

**Complexity**: 🟢 4/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Document disaster recovery and failover procedures.

#### Acceptance Criteria
- [x] AC1: RTO and RPO targets documented
- [x] AC2: Database failover steps
- [x] AC3: Service failover steps
- [x] AC4: Communication plan
- [x] AC5: Runbook for on-call engineers

#### Target Files
- `docs/DISASTER_RECOVERY.md`

---

## Accessibility (T344-T346)

### T344: Add axe-core accessibility tests

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: TEST

#### Objective
Add automated accessibility testing with axe-core.

#### Acceptance Criteria
- [x] AC1: axe-core integrated with Playwright
- [x] AC2: Tests run on all page routes
- [x] AC3: Zero critical violations
- [x] AC4: Violations logged with fixes
- [x] AC5: CI/CD integration

#### Target Files
- `frontend/e2e/accessibility.spec.ts`

---

### T345: Create keyboard navigation tests

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: TEST

#### Objective
Test keyboard navigation across the application.

#### Acceptance Criteria
- [x] AC1: Tab order is logical
- [x] AC2: Focus indicators visible
- [x] AC3: Escape closes modals
- [x] AC4: Arrow keys work in lists
- [x] AC5: Shortcuts documented and working

#### Target Files
- `frontend/e2e/keyboard-navigation.spec.ts`

---

### T346: Add screen reader ARIA audit checklist

**Complexity**: 🟢 5/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create ARIA audit checklist and fix issues.

#### Acceptance Criteria
- [x] AC1: All interactive elements have labels
- [x] AC2: Landmarks properly defined
- [x] AC3: Live regions for dynamic content
- [x] AC4: Proper heading hierarchy
- [x] AC5: Form fields have associated labels

#### Target Files
- `docs/ARIA_AUDIT.md`
- `frontend/src/components/**/*.tsx` (ARIA fixes)

---

## Human-in-the-Loop (T354-T356)

### T354: Create ApprovalDialog component

**Complexity**: 🟡 7/20 | **Priority**: P1 | **Story**: N/A
**Type**: IMPL

#### Objective
Create approval dialog for critical AI actions per DD-003.

#### Acceptance Criteria
- [x] AC1: `frontend/src/components/ai/ApprovalDialog.tsx` exists
- [x] AC2: Shows action details and consequences
- [x] AC3: Approve/Reject buttons with loading state
- [x] AC4: Timeout countdown (24h expiry)
- [x] AC5: Keyboard accessible (Enter=approve, Escape=reject)
- [x] AC6: Accessible with screen readers

#### Guidelines
```typescript
function ApprovalDialog({ approval, onApprove, onReject }: Props) {
  const [isApproving, setIsApproving] = useState(false);

  return (
    <Dialog open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve AI Action</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>The AI wants to: {approval.actionDescription}</p>
          <Alert variant="warning">
            This action will: {approval.consequences}
          </Alert>
          <p className="text-muted-foreground">
            Expires in: <CountdownTimer endTime={approval.expiresAt} />
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onReject}>
            Reject
          </Button>
          <Button onClick={onApprove} loading={isApproving}>
            Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

#### Target Files
- `frontend/src/components/ai/ApprovalDialog.tsx`

---

### T355: Create useApprovalFlow hook

**Complexity**: 🟡 6/20 | **Priority**: P1 | **Story**: N/A
**Type**: IMPL

#### Objective
Create React hook for managing approval flow state.

#### Acceptance Criteria
- [x] AC1: `useApprovalFlow` hook exists
- [x] AC2: Polls for pending approvals
- [x] AC3: Handles approve/reject mutations
- [x] AC4: Realtime subscription for new approvals
- [x] AC5: Toast notification on new approval

#### Guidelines
```typescript
function useApprovalFlow() {
  const { data: pendingApprovals } = usePendingApprovals();
  const approveMutation = useApproveMutation();
  const rejectMutation = useRejectMutation();

  // Subscribe to new approvals via Supabase Realtime
  useEffect(() => {
    const channel = supabase
      .channel('approvals')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'pending_approvals' },
        (payload) => {
          toast.info('New action requires approval');
        }
      )
      .subscribe();

    return () => { channel.unsubscribe(); };
  }, []);

  return {
    pendingApprovals,
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
  };
}
```

#### Target Files
- `frontend/src/hooks/useApprovalFlow.ts`

---

### T356: Add approval integration to modals

**Complexity**: 🟡 7/20 | **Priority**: P1 | **Story**: N/A
**Type**: IMPL

#### Objective
Integrate approval flow into critical action modals.

#### Acceptance Criteria
- [x] AC1: Delete confirmation triggers approval for bulk delete
- [x] AC2: Merge duplicate triggers approval
- [x] AC3: AI bulk update triggers approval
- [x] AC4: Shows pending status when awaiting approval
- [x] AC5: Handles timeout gracefully

#### Target Files
- `frontend/src/components/issues/DeleteConfirmDialog.tsx`
- `frontend/src/components/issues/MergeDuplicateDialog.tsx`
- `frontend/src/components/issues/BulkUpdateDialog.tsx`

---

## Data Export/Import (T357-T360)

### T357: Create JSON schema definitions

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create JSON schema for workspace export format.

#### Acceptance Criteria
- [x] AC1: Schema includes all entity types
- [x] AC2: Version field for schema evolution
- [x] AC3: References between entities use IDs
- [x] AC4: Excludes sensitive data (tokens, passwords)
- [x] AC5: Schema validation with jsonschema

#### Guidelines
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PilotSpaceExport",
  "version": "1.0.0",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "exportedAt": { "type": "string", "format": "date-time" },
    "workspace": { "$ref": "#/definitions/Workspace" },
    "projects": { "type": "array", "items": { "$ref": "#/definitions/Project" } },
    "issues": { "type": "array", "items": { "$ref": "#/definitions/Issue" } },
    "notes": { "type": "array", "items": { "$ref": "#/definitions/Note" } }
  },
  "required": ["version", "exportedAt", "workspace"]
}
```

#### Target Files
- `backend/src/pilot_space/schemas/export_schema.json`
- `backend/src/pilot_space/api/v1/schemas/export.py`

---

### T358: Create ExportWorkspaceService

**Complexity**: 🟡 8/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create service for exporting workspace data.

#### Acceptance Criteria
- [x] AC1: `ExportWorkspaceService` exists
- [x] AC2: Exports all workspace entities
- [x] AC3: Streaming export for large workspaces
- [x] AC4: Progress tracking for async export
- [x] AC5: Excludes integration credentials
- [x] AC6: ZIP format with JSON files

#### Guidelines
```python
class ExportWorkspaceService:
    async def export(self, workspace_id: UUID) -> AsyncGenerator[bytes, None]:
        """Stream workspace export as ZIP."""
        workspace = await self.workspace_repo.get(workspace_id)

        with io.BytesIO() as buffer:
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Export each entity type
                zf.writestr('workspace.json', self._serialize_workspace(workspace))
                zf.writestr('projects.json', await self._export_projects(workspace_id))
                zf.writestr('issues.json', await self._export_issues(workspace_id))
                zf.writestr('notes.json', await self._export_notes(workspace_id))

            buffer.seek(0)
            yield buffer.read()
```

#### Target Files
- `backend/src/pilot_space/application/services/export_workspace_service.py`

---

### T359: Create ImportWorkspaceService

**Complexity**: 🟡 9/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Create service for importing workspace data.

#### Acceptance Criteria
- [x] AC1: `ImportWorkspaceService` exists
- [x] AC2: Validates against JSON schema
- [x] AC3: Handles ID remapping for new workspace
- [x] AC4: Transactional import (all or nothing)
- [x] AC5: Conflict resolution: skip, overwrite, or fail
- [x] AC6: Progress tracking for async import

#### Guidelines
```python
class ImportWorkspaceService:
    async def import_workspace(
        self,
        user_id: UUID,
        file: UploadFile,
        conflict_mode: ConflictMode = ConflictMode.FAIL,
    ) -> ImportResult:
        """Import workspace from ZIP export."""
        # Validate schema
        data = await self._parse_and_validate(file)

        async with self.session.begin():
            # Create new workspace
            workspace = await self._create_workspace(data['workspace'], user_id)

            # Import entities with ID remapping
            id_map = {}
            id_map.update(await self._import_projects(data['projects'], workspace.id))
            id_map.update(await self._import_issues(data['issues'], id_map))
            id_map.update(await self._import_notes(data['notes'], id_map))

        return ImportResult(workspace_id=workspace.id, entity_counts={...})
```

#### Target Files
- `backend/src/pilot_space/application/services/import_workspace_service.py`

---

### T360: Add export/import endpoints

**Complexity**: 🟡 6/20 | **Priority**: P2 | **Story**: N/A
**Type**: IMPL

#### Objective
Add API endpoints for workspace export/import.

#### Acceptance Criteria
- [x] AC1: `POST /api/v1/workspaces/{id}/export` triggers export
- [x] AC2: `GET /api/v1/workspaces/exports/{job_id}` downloads export
- [x] AC3: `POST /api/v1/workspaces/import` uploads and imports
- [x] AC4: `GET /api/v1/workspaces/imports/{job_id}` checks import status
- [x] AC5: Rate limited: 1 export/import per hour
- [x] AC6: Admin-only permissions

#### Target Files
- `backend/src/pilot_space/api/v1/routers/workspaces.py`
- `backend/src/pilot_space/api/v1/schemas/export.py`

---

## Summary

| Category | Tasks | Complexity Range |
|----------|-------|------------------|
| Testing | T323-T329d (11) | 🟢5 - 🟡8 |
| Documentation | T330-T332 (3) | 🟢4 - 🟡6 |
| Performance | T333-T335 (3) | 🟡7 - 🟠12 |
| Security | T336-T337 (2) | 🟢5 - 🟡7 |
| Infrastructure | T338-T343 (6) | 🟢4 - 🟡8 |
| Accessibility | T344-T346 (3) | 🟢5 - 🟡6 |
| Human-in-the-Loop | T354-T356 (3) | 🟡6 - 🟡7 |
| Data Export/Import | T357-T360 (4) | 🟡6 - 🟡9 |
| **Total** | **38 tasks** | **avg 6.3/20** |
