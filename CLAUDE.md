# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a documentation repository (`pilot-space`) containing comprehensive architectural documentation for **Plane** - an open-source project management tool. The repository does not contain application code; it serves as a reference for understanding Plane's architecture, data models, and feature implementations.

## Repository Structure

```
pilot-space/
└── docs/
    ├── DATABASE_SCHEMA.md           # Complete database model documentation
    ├── AUTHENTICATION_ARCHITECTURE.md # Auth system (OAuth, magic links, sessions)
    ├── ISSUES_ARCHITECTURE.md       # Work items/issues feature
    ├── CYCLES_ARCHITECTURE.md       # Sprint/cycle management
    ├── MODULES_ARCHITECTURE.md      # Module/epic grouping
    ├── PAGES_ARCHITECTURE.md        # Wiki/documentation (Y.js CRDT)
    ├── VIEWS_ARCHITECTURE.md        # Saved filters and views
    ├── WORKSPACES_ARCHITECTURE.md   # Multi-tenant workspace system
    ├── NOTIFICATIONS_ARCHITECTURE.md # Notification delivery system
    ├── DEPENDENCY_GRAPH.md          # Feature dependency relationships
    └── FEATURES_ANALYSIS.md         # Complete feature breakdown with pricing tiers
```

## Plane Architecture Summary

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, React Router 7, MobX, Tailwind CSS, TipTap Editor |
| Backend | Django 4.2, Django REST Framework, Celery |
| Database | PostgreSQL with soft deletion pattern |
| Real-time | Y.js CRDTs + HocusPocus over WebSocket |
| Cache/Queue | Redis, RabbitMQ |
| Storage | S3-compatible (AWS S3 or MinIO) |

### Application Structure (Plane monorepo)

```
plane/
├── apps/
│   ├── web/           # Main app (port 3000)
│   ├── admin/         # Admin panel (port 3001)
│   ├── space/         # Public workspace view (port 3002)
│   ├── api/           # Django REST API
│   └── live/          # Real-time collaboration server
├── packages/
│   ├── ui/            # Shared component library
│   ├── types/         # TypeScript definitions
│   ├── services/      # API service layer
│   ├── editor/        # TipTap rich text editor
│   └── ...
```

### Key Architectural Patterns

**Database Patterns:**
- UUID primary keys on all models
- Soft deletion via `deleted_at` timestamp with `SoftDeletionManager`
- Audit trail: `created_at`, `updated_at`, `created_by`, `updated_by`
- PostgreSQL advisory locks for issue sequence ID generation

**Frontend Patterns:**
- MobX stores for state management (not Redux)
- Service classes wrapping Axios for API calls
- React Router v7 with file-based routing

**Real-time Collaboration:**
- Y.js CRDTs for conflict-free document synchronization
- HocusPocus server handles WebSocket connections
- Binary CRDT state stored in `description_binary` fields

### Core Domain Models

| Model | Purpose |
|-------|---------|
| Workspace | Top-level tenant container |
| Project | Container for issues, cycles, modules |
| Issue | Work items with states, priorities, assignees |
| Cycle | Time-boxed sprints |
| Module | Feature/epic grouping |
| Page | Documentation with real-time collaboration |
| State | Custom workflow stages per project |

### Data Flow Pattern

```
User Action → Service Layer → Django REST API → PostgreSQL
                                    ↓
                           Celery Background Tasks
                                    ↓
                    Webhooks, Notifications, Activity Logs
```

## Working with This Repository

### When Researching Plane Features

1. Start with `FEATURES_ANALYSIS.md` for feature overview and pricing tiers
2. Use `DATABASE_SCHEMA.md` for model relationships and field definitions
3. Reference specific `*_ARCHITECTURE.md` files for deep dives into subsystems
4. Check `DEPENDENCY_GRAPH.md` for understanding feature interdependencies

### Key Documentation Entry Points

- **Understanding the data model**: `DATABASE_SCHEMA.md` - Core Design Patterns section
- **Authentication flows**: `AUTHENTICATION_ARCHITECTURE.md` - Adapters & Providers section
- **Issue lifecycle**: `ISSUES_ARCHITECTURE.md` - Business Logic & Workflows section
- **Real-time editing**: `PAGES_ARCHITECTURE.md` - Real-Time Collaboration section
- **CE vs EE features**: `FEATURES_ANALYSIS.md` - Subscription Tiers section

### Cross-Reference Patterns

The documentation uses consistent patterns:
- File paths reference the Plane codebase (e.g., `apps/api/plane/db/models/issue.py`)
- API endpoints are documented with method, path, and purpose
- MobX stores follow `*.store.ts` naming convention
- Services follow `*.service.ts` naming convention
