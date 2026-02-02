# Project Analysis Checklist

This checklist provides a systematic approach to analyzing project context before generating clarification questions.

## Discovery Process Overview

```
Phase 1: Repository Structure → Phase 2: Tech Stack → Phase 3: Architecture →
Phase 4: Domain Knowledge → Phase 5: Patterns & Conventions → Synthesize Context Summary
```

---

## Phase 1: Repository Structure Analysis

### 1.1 Directory Layout

**Objective**: Understand project organization and identify key components

**Files to Examine**:
- [ ] Root directory contents (`ls -la`)
- [ ] README.md (if exists)
- [ ] CLAUDE.md or PROJECT.md (project-specific instructions)
- [ ] .gitignore (identifies generated files, secrets patterns)

**Key Questions**:
- [ ] Is this a monorepo or single-project structure?
- [ ] Where is source code located? (`src/`, `apps/`, `packages/`, etc.)
- [ ] Are there separate directories for different services/modules?
- [ ] Is there a `docs/` directory with additional documentation?

**Output**: Repository structure map
```
Example:
- Monorepo with apps/ and libs/
- Source code: apps/{service-name}/src/ubits/{service_name}/
- Documentation: docs/
- Shared code: libs/{library-name}/src/ubits/{library_name}/
```

### 1.2 Build Configuration

**Objective**: Identify build tools, package managers, and project metadata

**Files to Examine**:
- [ ] **Python**: `pyproject.toml`, `requirements.txt`, `setup.py`, `poetry.lock`, `uv.lock`
- [ ] **Node.js**: `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`
- [ ] **Go**: `go.mod`, `go.sum`
- [ ] **Rust**: `Cargo.toml`, `Cargo.lock`
- [ ] **Java**: `pom.xml`, `build.gradle`, `build.gradle.kts`
- [ ] **Monorepo**: `nx.json`, `turbo.json`, `lerna.json`, `pnpm-workspace.yaml`

**Key Information to Extract**:
- [ ] Primary language(s) and versions
- [ ] Package manager (npm, yarn, pnpm, pip, uv, poetry, cargo, etc.)
- [ ] Build tool (nx, turbo, make, etc.)
- [ ] Key dependencies and frameworks
- [ ] Development vs production dependencies

**Output**: Tech stack summary
```
Example:
- Python 3.12+ with uv package manager
- FastAPI (web framework), SQLAlchemy 2.0 (ORM), Pydantic v2 (validation)
- Monorepo managed by Nx
- Development: pytest, ruff, pyright, black
```

---

## Phase 2: Architecture Discovery

### 2.1 System Architecture Documentation

**Objective**: Understand high-level system design and architectural patterns

**Files to Examine**:
- [ ] `docs/architecture.md`, `docs/ARCHITECTURE.md`
- [ ] `CLAUDE.md`, `PROJECT.md` (often contains architecture overview)
- [ ] README.md (architecture section)
- [ ] `docs/dev-pattern/*.md` (if exists)

**Key Questions**:
- [ ] What is the architectural style? (Microservices, monolith, event-driven, layered, etc.)
- [ ] Are there multiple tiers or layers? (Edge, Worker, Data Center, etc.)
- [ ] What are the communication patterns? (REST, gRPC, Kafka, message queues, etc.)
- [ ] Are there architectural constraints or rules? (No X, Must use Y, etc.)

**Common Architectural Patterns to Identify**:
- [ ] **Microservices**: Multiple independent services with separate deployments
- [ ] **Event-Driven**: Kafka, RabbitMQ, event sourcing, CQRS
- [ ] **Layered**: Presentation → Business Logic → Data Access
- [ ] **Multi-Tier**: Edge/Worker/Data Center, Client/Server, n-tier
- [ ] **Domain-Driven**: Bounded contexts, aggregates, domain events

**Output**: Architecture summary
```
Example:
- Three-tier architecture: Edge K3s → Worker (GPU) → Data Center
- Inter-tier communication: Kafka ONLY (no HTTP between tiers)
- Microservices: 6 services on ports 8001-8006
- Patterns: Repository pattern, service layer, dependency injection
- Constraints: Tier 3 never accesses raw camera data
```

### 2.2 Infrastructure and Deployment

**Objective**: Understand deployment environment and infrastructure patterns

**Files to Examine**:
- [ ] `docker-compose.yml`, `Dockerfile`, `.dockerignore`
- [ ] `kubernetes/`, `k8s/` directories (manifests, helm charts)
- [ ] `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile` (CI/CD pipelines)
- [ ] `terraform/`, `pulumi/` (infrastructure as code)

**Key Questions**:
- [ ] Containerized deployment? (Docker, Kubernetes, etc.)
- [ ] CI/CD pipeline present?
- [ ] Infrastructure as code?
- [ ] Environment configuration management?

**Output**: Deployment context
```
Example:
- Kubernetes: Multi-cluster (K3s at edge, K8s in data center)
- Docker: Services containerized
- CI/CD: GitHub Actions with pytest, ruff, pyright gates
- Infrastructure: Terraform for cloud resources
```

---

## Phase 3: Domain Knowledge Extraction

### 3.1 Domain Models and Entities

**Objective**: Understand the business domain and core entities

**Files to Examine**:
- [ ] `models.py`, `entities.py`, `schemas.py` (database models)
- [ ] `domain/`, `entities/` directories
- [ ] `docs/domain-model.md`, `docs/data-model.md`
- [ ] Database migration files (`alembic/`, `migrations/`, `flyway/`)

**Key Questions**:
- [ ] What are the core entities/aggregates? (User, Camera, Event, Order, etc.)
- [ ] What are the relationships between entities?
- [ ] What are the key domain events?
- [ ] Are there domain-specific business rules?

**Common Domain Patterns**:
- [ ] **Multi-tenancy**: `tenant_id` in models, row-level security
- [ ] **Soft deletes**: `deleted_at` timestamp instead of physical deletion
- [ ] **Audit trails**: `created_at`, `updated_at`, `created_by`, `updated_by`
- [ ] **Status enums**: Workflow states (pending, active, completed, etc.)
- [ ] **Versioning**: `version` field for optimistic locking

**Output**: Domain model summary
```
Example:
- Core entities: User, Camera, CameraConfig, DetectionEvent, AnalyticsReport
- Multi-tenant: All entities have tenant_id
- Audit: created_at, updated_at on all entities
- Key relationships: User → Camera (1:many), Camera → DetectionEvent (1:many)
- Business rules: GDPR (hash license plates), 30-day retention (events)
```

### 3.2 API Contracts and Endpoints

**Objective**: Understand public APIs and service contracts

**Files to Examine**:
- [ ] `api/`, `endpoints/`, `controllers/` directories
- [ ] `openapi.yaml`, `swagger.json` (API specifications)
- [ ] `routers.py`, `routes.py` (endpoint definitions)
- [ ] `docs/api/` (API documentation)

**Key Questions**:
- [ ] What API style? (REST, GraphQL, gRPC, etc.)
- [ ] Versioned endpoints? (`/api/v1/`, `/api/v2/`, etc.)
- [ ] Authentication/authorization pattern?
- [ ] Request/response payload structures?

**Output**: API contract summary
```
Example:
- REST API with FastAPI
- Versioned: /api/v1/{resource}
- Auth: JWT tokens with permission-based middleware
- Pagination: Standard limit/offset pattern
- Error format: RFC 7807 Problem Details
```

---

## Phase 4: Code Patterns and Conventions

### 4.1 Code Standards

**Objective**: Identify coding conventions and standards

**Files to Examine**:
- [ ] `CLAUDE.md`, `.claude/` directory (AI agent instructions)
- [ ] `docs/dev-pattern/`, `docs/coding-standards.md`
- [ ] `.editorconfig` (formatting rules)
- [ ] Linter configs: `.ruff.toml`, `.eslintrc`, `tslint.json`, `.pylintrc`
- [ ] Formatter configs: `.prettierrc`, `pyproject.toml` (black settings)

**Key Standards to Identify**:
- [ ] **Naming conventions**: snake_case, camelCase, PascalCase patterns
- [ ] **File organization**: Modules, packages, directory structure
- [ ] **Import conventions**: Absolute vs relative, ordering rules
- [ ] **Type annotations**: Strict typing requirements
- [ ] **Documentation**: Docstring style (Google, NumPy, reStructuredText)

**Common Project-Specific Rules**:
- [ ] Namespace requirements (e.g., `ubits.*` instead of `src.*`)
- [ ] File size limits (e.g., 700 lines max)
- [ ] Async/await requirements for I/O operations
- [ ] Test coverage thresholds (e.g., >95%)

**Output**: Coding standards summary
```
Example:
- Namespace: ALL imports use `ubits.*` (NEVER `src.*`)
- File size: 700 lines max (components), 1400 max (tests)
- Async: MUST use async/await for ALL I/O operations
- Types: Full type annotations required (pyright strict mode)
- Testing: >95% coverage (pytest --cov-fail-under=95)
- Formatting: black --line-length=100
```

### 4.2 Design Patterns in Use

**Objective**: Identify established design patterns to maintain consistency

**Files to Examine**:
- [ ] `repositories/`, `services/`, `factories/` directories
- [ ] Base classes: `base_repository.py`, `base_service.py`
- [ ] Dependency injection: `dependencies.py`, `container.py`
- [ ] Middleware: `middleware/`, `interceptors/`

**Common Patterns to Look For**:
- [ ] **Repository Pattern**: Data access abstraction
- [ ] **Service Layer**: Business logic coordination
- [ ] **Factory Pattern**: Object creation
- [ ] **Dependency Injection**: Protocol-based DI, FastAPI Depends()
- [ ] **Strategy Pattern**: Pluggable algorithms
- [ ] **Observer Pattern**: Event handlers, listeners

**Output**: Design pattern inventory
```
Example:
- Repository Pattern: Base repository at libs/database/repositories/base.py
- Service Layer: Async context managers with atomic transactions
- Dependency Injection: Protocol-based, FastAPI Depends()
- N+1 Prevention: selectinload() for eager loading (standard)
- Error Handling: Custom exceptions with RFC 7807 problem details
```

---

## Phase 5: Testing and Quality Patterns

### 5.1 Test Organization

**Objective**: Understand test structure and conventions

**Files to Examine**:
- [ ] `tests/`, `test/`, `__tests__/` directories
- [ ] `conftest.py` (pytest fixtures)
- [ ] Test configuration: `pytest.ini`, `jest.config.js`, `karma.conf.js`
- [ ] `docs/testing-standards.md`, `docs/dev-pattern/03-testing-standards.md`

**Key Patterns**:
- [ ] **Test naming**: Convention for test function names
- [ ] **Test organization**: Unit, integration, E2E separation
- [ ] **Fixtures**: Shared test data and setup
- [ ] **Mocking strategy**: What gets mocked vs real dependencies
- [ ] **Test coverage**: Target percentage and enforcement

**Output**: Testing pattern summary
```
Example:
- Naming: test_that_{component}_{action}_{expected_result}
- Structure: tests/{module}/test_{file}.py mirrors src/{module}/{file}.py
- Coverage: >95% required (CI enforced)
- Fixtures: conftest.py with shared async DB fixtures
- TDD: Tests written BEFORE implementation (non-negotiable)
```

### 5.2 Quality Gates

**Objective**: Identify automated quality checks

**Files to Examine**:
- [ ] `.pre-commit-config.yaml` (pre-commit hooks)
- [ ] CI configuration files (GitHub Actions, GitLab CI, etc.)
- [ ] `Makefile`, `scripts/validate.sh` (validation scripts)

**Quality Gates to Identify**:
- [ ] **Type checking**: mypy, pyright, TypeScript compiler
- [ ] **Linting**: ruff, eslint, pylint, golangci-lint
- [ ] **Formatting**: black, prettier, rustfmt
- [ ] **Security scanning**: bandit, safety, npm audit
- [ ] **Test execution**: pytest, jest, go test
- [ ] **Coverage thresholds**: Minimum coverage percentage

**Output**: Quality gate checklist
```
Example:
6 Quality Gates (ALL must pass before commit):
1. Type safety: uv run pyright (zero errors)
2. Code quality: ruff check . (zero violations)
3. Formatting: black --line-length=100 .
4. Test coverage: pytest --cov=src --cov-fail-under=95
5. Performance: No N+1 queries, no blocking I/O
6. Architecture: ubits.* namespace, <700 lines, three-tier compliance
```

---

## Phase 6: Synthesis

### 6.1 Context Summary Generation

**Objective**: Compile all discovered information into actionable context

**Template**:
```markdown
# Project Context Summary

## Tech Stack
- **Languages**: [List with versions]
- **Frameworks**: [Key frameworks]
- **Databases**: [DB types and versions]
- **Infrastructure**: [Deployment environment]

## Architecture
- **Style**: [Microservices/Monolith/Event-driven/etc.]
- **Patterns**: [Key architectural patterns]
- **Communication**: [Inter-service communication methods]
- **Constraints**: [Critical architectural rules]

## Domain
- **Core Entities**: [List of main entities]
- **Key Relationships**: [Important entity relationships]
- **Business Rules**: [Critical business constraints]
- **Regulatory**: [Compliance requirements if any]

## Code Standards
- **Namespace**: [Import conventions]
- **File Size**: [Limits if any]
- **Async/Sync**: [I/O operation requirements]
- **Type Safety**: [Type annotation requirements]
- **Testing**: [Coverage and TDD requirements]

## Design Patterns
- **Data Access**: [Repository/DAO/ORM patterns]
- **Business Logic**: [Service layer patterns]
- **Dependency Injection**: [DI approach]
- **Error Handling**: [Exception patterns]

## Quality Gates
- [List of automated checks]
- [Coverage requirements]
- [Performance SLAs]

## API Contracts
- **Style**: [REST/GraphQL/gRPC]
- **Versioning**: [API versioning approach]
- **Auth**: [Authentication/authorization patterns]
- **Error Format**: [Standardized error responses]

## Key Files Reference
- Architecture: [Path to architecture docs]
- Standards: [Path to coding standards]
- Patterns: [Path to pattern library]
- Domain Models: [Path to entity definitions]
- Base Classes: [Path to base repository/service]
```

### 6.2 Pattern Matching Preparation

**Objective**: Prepare discovered patterns for scoring algorithm

**For each common pattern category, extract**:
- **File path**: Exact location of pattern implementation
- **Line numbers**: Specific implementation location
- **Usage frequency**: How many times pattern is used
- **Variations**: Any deviations from the standard pattern

**Output**: Pattern reference database
```
Example:
{
  "repository_pattern": {
    "base": "libs/database/src/ubits/database/repositories/base.py:22-259",
    "usage_count": 23,
    "variations": ["auth-specific: includes permission checking"]
  },
  "service_layer": {
    "base": "apps/auth-service/src/ubits/auth_service/services/user_service.py",
    "usage_count": 15,
    "pattern": "Async context manager with atomic transactions"
  },
  "n_plus_one_prevention": {
    "example": "libs/database/src/ubits/database/repositories/camera.py:346-371",
    "technique": "selectinload() for one-to-many relationships",
    "usage_count": 18
  }
}
```

---

## Checklist Summary

Use this quick-reference checklist during analysis:

### Quick Discovery Checklist

- [ ] **Phase 1: Structure** - ls root, read README, identify monorepo vs single-project
- [ ] **Phase 2: Tech Stack** - Check package manifests, identify languages/frameworks/tools
- [ ] **Phase 3: Architecture** - Read CLAUDE.md, docs/architecture.md, identify patterns and constraints
- [ ] **Phase 4: Domain** - Examine models, API contracts, business rules
- [ ] **Phase 5: Patterns** - Identify coding standards, design patterns, test conventions
- [ ] **Phase 6: Synthesis** - Compile context summary, prepare pattern matching database

### Information Gathering Priorities

**For Simple Requests** (quick features, minor changes):
- Minimum: Tech stack + code standards + relevant design pattern
- Time: ~2-3 minutes
- Files: 3-5 key files

**For Complex Requests** (new services, architectural changes):
- Full analysis: All phases
- Time: ~5-10 minutes
- Files: 10-20 files across categories

**For Ambiguous Requests** (unclear scope, vague requirements):
- Focus: Architecture constraints + domain models + existing patterns
- Time: ~3-5 minutes
- Files: 5-10 strategic files

### Common Mistakes to Avoid

❌ **Don't**: Read entire codebase sequentially
✅ **Do**: Strategic file selection based on request type

❌ **Don't**: Assume patterns without verification
✅ **Do**: Reference actual files with line numbers

❌ **Don't**: Generate questions without context
✅ **Do**: Ground questions in discovered project patterns

❌ **Don't**: Overwhelm with all discovered information
✅ **Do**: Present only relevant context for the specific request
