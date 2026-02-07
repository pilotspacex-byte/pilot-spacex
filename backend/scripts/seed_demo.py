"""Comprehensive demo data seeding script.

This unified script:
1. Creates Supabase Auth user via Admin API
2. Seeds database with demo data using the Auth user ID
3. Creates workspace, projects, notes, issues, and labels

Run this script to set up a complete demo environment:
    python backend/scripts/seed_demo.py

Requirements:
- Supabase local instance running (docker compose up)
- SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment
- Database migrations applied (alembic upgrade head)
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta

import dotenv
import httpx
from sqlalchemy import text

from pilot_space.infrastructure.database.engine import get_db_session

# Load environment variables
dotenv.load_dotenv()

# Demo configuration
DEMO_EMAIL = "test@pilot.space"
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "DemoPassword123!")
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:18000")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def create_tiptap_note(paragraphs: list[str]) -> dict:
    """Create TipTap JSON document from paragraphs."""
    content = []
    for para in paragraphs:
        if para.strip():
            content.append({"type": "paragraph", "content": [{"type": "text", "text": para}]})
    return {"type": "doc", "content": content}


async def create_or_get_auth_user() -> uuid.UUID:
    """Create or get existing Supabase Auth user.

    Returns:
        UUID of the Auth user (existing or newly created).
    """
    if not SUPABASE_SERVICE_KEY:
        print("❌ ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable not set")
        print("   Set it in backend/.env or run: export SUPABASE_SERVICE_ROLE_KEY=<key>")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🔐 STEP 1: SUPABASE AUTH USER")
    print("=" * 60 + "\n")

    auth_admin_url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            # Check if user already exists
            print("🔍 Checking if auth user already exists...")
            list_response = await client.get(
                auth_admin_url,
                headers=headers,
                timeout=10.0,
            )

            if list_response.status_code == 200:
                users = list_response.json().get("users", [])
                existing_user = next((u for u in users if u.get("email") == DEMO_EMAIL), None)

                if existing_user:
                    user_id = uuid.UUID(existing_user["id"])
                    print(f"✅ Found existing auth user: {user_id}")
                    print(f"   Email: {DEMO_EMAIL}")
                    return user_id

            # Create new auth user
            print(f"🚀 Creating new auth user for {DEMO_EMAIL}...")
            payload = {
                "email": DEMO_EMAIL,
                "password": DEMO_PASSWORD,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": "Tin Dang",
                },
            }

            response = await client.post(
                auth_admin_url,
                headers=headers,
                json=payload,
                timeout=10.0,
            )

            if response.status_code in (200, 201):
                user_data = response.json()
                user_id = uuid.UUID(user_data["id"])
                print(f"✅ Created auth user: {user_id}")
                print(f"   Email: {DEMO_EMAIL}")
                print(f"   Password: {DEMO_PASSWORD}")
                return user_id

            print(f"\n❌ ERROR: Failed to create auth user (status {response.status_code})")
            print(f"   Response: {response.text}")
            sys.exit(1)

        except httpx.TimeoutException:
            print("\n❌ ERROR: Request timed out")
            print("   Is Supabase running? Check: docker compose ps")
            sys.exit(1)
        except httpx.ConnectError:
            print(f"\n❌ ERROR: Cannot connect to Supabase at {SUPABASE_URL}")
            print("   Is Supabase running? Start with: docker compose up -d")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            sys.exit(1)


async def seed_database(demo_user_id: uuid.UUID) -> None:
    """Seed comprehensive demo data into the database.

    Args:
        demo_user_id: The Supabase Auth user ID to use for all records.
    """
    async with get_db_session() as session:
        print("\n" + "=" * 60)
        print("🌱 STEP 2: SEEDING DATABASE")
        print("=" * 60 + "\n")

        # Check if demo data already exists
        result = await session.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": demo_user_id},
        )
        if result.scalar_one_or_none():
            print("⚠️  Demo data already exists. Clearing and reseeding...")
            # Delete workspace first (CASCADE will handle related data)
            await session.execute(
                text("DELETE FROM workspaces WHERE id = :id"),
                {"id": DEMO_WORKSPACE_ID},
            )
            # Delete user
            await session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": demo_user_id},
            )
            await session.commit()

        # ===================================================================
        # Create Demo User (matches Auth user)
        # ===================================================================
        await session.execute(
            text("""
                INSERT INTO users (id, email, full_name, avatar_url, created_at, updated_at, is_deleted)
                VALUES (:id, :email, :full_name, :avatar_url, NOW(), NOW(), false)
            """),
            {
                "id": demo_user_id,
                "email": DEMO_EMAIL,
                "full_name": "Tin Dang",
                "avatar_url": None,
            },
        )
        print(f"✅ Created database user: {demo_user_id}")

        # ===================================================================
        # Create Demo Workspace
        # ===================================================================
        await session.execute(
            text("""
                INSERT INTO workspaces (id, name, slug, description, owner_id, settings, created_at, updated_at, is_deleted)
                VALUES (:id, :name, :slug, :description, :owner_id, :settings, NOW(), NOW(), false)
            """),
            {
                "id": DEMO_WORKSPACE_ID,
                "name": "Pilot Space",
                "slug": "pilot-space-demo",
                "description": "AI-Augmented SDLC Platform Demo Workspace",
                "owner_id": demo_user_id,
                "settings": json.dumps({}),
            },
        )
        print("✅ Created workspace: pilot-space-demo")

        # Add user as workspace owner
        await session.execute(
            text("""
                INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at, updated_at, is_deleted)
                VALUES (:id, :workspace_id, :user_id, 'OWNER', NOW(), NOW(), false)
            """),
            {
                "id": uuid.uuid4(),
                "workspace_id": DEMO_WORKSPACE_ID,
                "user_id": demo_user_id,
            },
        )

        # ===================================================================
        # Create 3 Projects
        # ===================================================================
        projects_data = [
            {
                "id": uuid.uuid4(),
                "name": "Authentication",
                "identifier": "AUTH",
                "description": "User auth and authorization system",
                "icon": "🔐",
            },
            {
                "id": uuid.uuid4(),
                "name": "API Gateway",
                "identifier": "API",
                "description": "REST API and GraphQL endpoints",
                "icon": "🌐",
            },
            {
                "id": uuid.uuid4(),
                "name": "Frontend",
                "identifier": "FE",
                "description": "React frontend application",
                "icon": "⚛️",
            },
        ]

        project_ids = {}
        for proj in projects_data:
            await session.execute(
                text("""
                    INSERT INTO projects (id, workspace_id, name, identifier, description, icon, lead_id, settings, created_at, updated_at, is_deleted)
                    VALUES (:id, :workspace_id, :name, :identifier, :description, :icon, :lead_id, :settings, NOW(), NOW(), false)
                """),
                {
                    "id": proj["id"],
                    "workspace_id": DEMO_WORKSPACE_ID,
                    "name": proj["name"],
                    "identifier": proj["identifier"],
                    "description": proj["description"],
                    "icon": proj["icon"],
                    "lead_id": demo_user_id,
                    "settings": json.dumps({}),
                },
            )
            project_ids[proj["identifier"]] = proj["id"]
            print(f"✅ Created project: {proj['name']} ({proj['identifier']})")

        # ===================================================================
        # Create Workflow States for Each Project
        # ===================================================================
        states_template = [
            {"name": "Backlog", "color": "#94a3b8", "group": "unstarted", "sequence": 0},
            {"name": "Todo", "color": "#3b82f6", "group": "unstarted", "sequence": 1},
            {"name": "In Progress", "color": "#f59e0b", "group": "started", "sequence": 2},
            {"name": "In Review", "color": "#a855f7", "group": "started", "sequence": 3},
            {"name": "Done", "color": "#22c55e", "group": "completed", "sequence": 4},
            {"name": "Cancelled", "color": "#ef4444", "group": "cancelled", "sequence": 5},
        ]

        state_ids = {}
        for proj_id_key, proj_id in project_ids.items():
            state_ids[proj_id_key] = {}
            for state in states_template:
                state_id = uuid.uuid4()
                await session.execute(
                    text("""
                        INSERT INTO states (id, workspace_id, project_id, name, color, "group", sequence, created_at, updated_at, is_deleted)
                        VALUES (:id, :workspace_id, :project_id, :name, :color, :group, :sequence, NOW(), NOW(), false)
                    """),
                    {
                        "id": state_id,
                        "workspace_id": DEMO_WORKSPACE_ID,
                        "project_id": proj_id,
                        "name": state["name"],
                        "color": state["color"],
                        "group": state["group"],
                        "sequence": state["sequence"],
                    },
                )
                state_ids[proj_id_key][state["name"]] = state_id
        print("✅ Created workflow states for all projects (6 states × 3 projects)")

        # ===================================================================
        # Create Labels
        # ===================================================================
        labels_data = [
            # Type labels
            {"name": "bug", "color": "#ef4444", "project": "AUTH"},
            {"name": "feature", "color": "#3b82f6", "project": "AUTH"},
            {"name": "enhancement", "color": "#8b5cf6", "project": "AUTH"},
            {"name": "bug", "color": "#ef4444", "project": "API"},
            {"name": "feature", "color": "#3b82f6", "project": "API"},
            {"name": "performance", "color": "#f59e0b", "project": "API"},
            {"name": "bug", "color": "#ef4444", "project": "FE"},
            {"name": "feature", "color": "#3b82f6", "project": "FE"},
            {"name": "ui", "color": "#ec4899", "project": "FE"},
            # Domain labels
            {"name": "backend", "color": "#10b981", "project": "AUTH"},
            {"name": "security", "color": "#dc2626", "project": "AUTH"},
            {"name": "graphql", "color": "#e11d48", "project": "API"},
            {"name": "rest", "color": "#059669", "project": "API"},
            {"name": "accessibility", "color": "#6366f1", "project": "FE"},
        ]

        label_ids = {}
        for label in labels_data:
            label_id = uuid.uuid4()
            proj_id = project_ids[label["project"]]
            await session.execute(
                text("""
                    INSERT INTO labels (id, workspace_id, project_id, name, color, created_at, updated_at, is_deleted)
                    VALUES (:id, :workspace_id, :project_id, :name, :color, NOW(), NOW(), false)
                """),
                {
                    "id": label_id,
                    "workspace_id": DEMO_WORKSPACE_ID,
                    "project_id": proj_id,
                    "name": label["name"],
                    "color": label["color"],
                },
            )
            label_key = f"{label['project']}:{label['name']}"
            label_ids[label_key] = label_id
        print(f"✅ Created {len(labels_data)} labels across projects")

        # ===================================================================
        # Create Notes with Realistic Content
        # ===================================================================
        notes_data = [
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
                "title": "Auth Refactor",
                "project": "AUTH",
                "is_pinned": True,
                "content": create_tiptap_note(
                    [
                        "# Authentication Refactor Planning",
                        "",
                        "We need to migrate from our current session-based auth to JWT tokens with refresh token rotation.",
                        "",
                        "## Current Issues",
                        "- Sessions stored in Redis, causing scale issues",
                        "- No refresh token mechanism",
                        "- OAuth2 providers not properly integrated",
                        "",
                        "## Proposed Solution",
                        "Implement JWT-based authentication with:",
                        "1. Access tokens (15 min TTL)",
                        "2. Refresh tokens (7 day TTL) with rotation",
                        "3. Supabase Auth integration for OAuth2",
                        "",
                        "## Security Considerations",
                        "- Store refresh tokens in httpOnly cookies",
                        "- Implement CSRF protection",
                        "- Add rate limiting on token endpoints",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
                "title": "API Design",
                "project": "API",
                "is_pinned": True,
                "content": create_tiptap_note(
                    [
                        "# API Gateway Architecture",
                        "",
                        "Designing our unified API gateway to handle both REST and GraphQL requests.",
                        "",
                        "## REST Endpoints",
                        "Following RESTful conventions:",
                        "- `/api/v1/workspaces` - Workspace management",
                        "- `/api/v1/projects` - Project CRUD",
                        "- `/api/v1/issues` - Issue tracking",
                        "- `/api/v1/notes` - Note management",
                        "",
                        "## GraphQL Schema",
                        "Considering GraphQL for complex queries with nested relationships.",
                        "Benefits: Reduced over-fetching, flexible queries, type safety",
                        "",
                        "## Rate Limiting",
                        "Implement per-workspace rate limits:",
                        "- Free tier: 1000 req/hour",
                        "- Pro tier: 10000 req/hour",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
                "title": "Sprint 12 Planning",
                "project": "AUTH",
                "is_pinned": False,
                "content": create_tiptap_note(
                    [
                        "# Sprint 12 - Authentication Focus",
                        "**Duration**: Feb 1-14, 2026",
                        "",
                        "## Goals",
                        "- Complete JWT migration",
                        "- Add Google OAuth2 provider",
                        "- Implement refresh token rotation",
                        "",
                        "## Team Capacity",
                        "- 2 backend engineers (full sprint)",
                        "- 1 frontend engineer (50% capacity)",
                        "",
                        "## Success Criteria",
                        "- All existing tests pass with JWT implementation",
                        "- OAuth2 flow tested with Google accounts",
                        "- Security audit completed",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000004"),
                "title": "Bug Triage Notes",
                "project": None,  # Workspace-level note
                "is_pinned": False,
                "content": create_tiptap_note(
                    [
                        "# Weekly Bug Triage - Week of Jan 22",
                        "",
                        "## Critical Bugs (P0)",
                        "1. Login timeout on slow connections - AUTH-45",
                        "2. GraphQL query returning null for nested fields - API-78",
                        "",
                        "## High Priority (P1)",
                        "1. Note editor losing focus on auto-save - FE-23",
                        "2. API rate limiting not working for workspace scope - API-80",
                        "",
                        "## Medium Priority (P2)",
                        "1. Dark mode colors inconsistent - FE-31",
                        "2. Email notifications delayed by 5+ minutes - Multiple components",
                        "",
                        "## Decisions",
                        "- P0 bugs must be fixed this week",
                        "- P1 bugs scheduled for Sprint 12",
                        "- P2 bugs moved to backlog",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000005"),
                "title": "Feature Spec: Search",
                "project": "FE",
                "is_pinned": False,
                "content": create_tiptap_note(
                    [
                        "# Global Search Feature Specification",
                        "",
                        "## User Story",
                        "As a user, I want to search across all my notes, issues, and projects so that I can quickly find relevant information.",
                        "",
                        "## Requirements",
                        "### Functional",
                        "- Search input accessible via keyboard shortcut (⌘K / Ctrl+K)",
                        "- Search across: Notes (title + content), Issues (title + description), Projects (name + description)",
                        "- Results grouped by entity type",
                        "- Real-time search with debouncing (300ms)",
                        "",
                        "### Non-Functional",
                        "- Search latency < 200ms for 10k documents",
                        "- Support fuzzy matching and typo tolerance",
                        "- Highlight search terms in results",
                        "",
                        "## Technical Approach",
                        "- Use Meilisearch for full-text search",
                        "- Index documents on create/update via background jobs",
                        "- Implement webhook for real-time index updates",
                        "",
                        "## Success Metrics",
                        "- 90% of searches return results in < 200ms",
                        "- Users find desired content in top 5 results 80% of the time",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000006"),
                "title": "Frontend Architecture Review",
                "project": "FE",
                "is_pinned": False,
                "content": create_tiptap_note(
                    [
                        "# Frontend Architecture - Tech Stack Review",
                        "",
                        "## Current Stack",
                        "- React 18 with TypeScript",
                        "- Next.js 14 (App Router)",
                        "- MobX for state management",
                        "- TanStack Query for server state",
                        "- TailwindCSS + shadcn/ui",
                        "",
                        "## Pain Points",
                        "1. MobX stores getting complex with nested observables",
                        "2. No clear pattern for optimistic updates",
                        "3. SSR hydration mismatches with dynamic content",
                        "",
                        "## Proposed Improvements",
                        "- Introduce feature-based store organization",
                        "- Standardize optimistic update patterns",
                        "- Use React Server Components for static content",
                        "",
                        "## Decision",
                        "Stick with current stack but refactor stores to follow cleaner patterns. Document best practices in wiki.",
                    ]
                ),
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000007"),
                "title": "AI Agent Integration Notes",
                "project": None,  # Workspace-level
                "is_pinned": False,
                "content": create_tiptap_note(
                    [
                        "# Claude Agent SDK Integration",
                        "",
                        "## Overview",
                        "Integrating Claude Agent SDK for AI-powered features:",
                        "- Ghost text suggestions in note editor",
                        "- Margin annotations for action items",
                        "- AI context generation for issues",
                        "- PR review with architecture analysis",
                        "",
                        "## Key Features Implemented",
                        "1. **Thread-Safe API Key Management**: Per-workspace API keys with per-event-loop locks",
                        "2. **Session Persistence**: Multi-turn conversations with 8000 token budget",
                        "3. **Human-in-the-Loop**: Three-tier approval workflow (auto-execute, require-approval, critical)",
                        "4. **Subagent Streaming**: Real-time SSE streaming for PR review, AI context, doc generation",
                        "",
                        "## Model Selection (DD-011)",
                        "- Code review: Claude Sonnet 4 (best reasoning)",
                        "- Ghost text: Gemini 2.0 Flash (lowest latency)",
                        "- Embeddings: OpenAI text-embedding-3-large",
                        "",
                        "## Next Steps",
                        "- Implement PilotSpaceAgent orchestrator",
                        "- Create 8 skills system (.claude/skills/)",
                        "- Build unified PilotSpaceStore for frontend",
                    ]
                ),
            },
        ]

        note_ids = {}
        for note_data in notes_data:
            proj_id = project_ids.get(note_data["project"]) if note_data["project"] else None
            await session.execute(
                text("""
                    INSERT INTO notes (id, workspace_id, project_id, title, content, owner_id, is_pinned, word_count, reading_time_mins, created_at, updated_at, is_deleted)
                    VALUES (:id, :workspace_id, :project_id, :title, :content, :owner_id, :is_pinned, :word_count, :reading_time_mins, :created_at, NOW(), false)
                """),
                {
                    "id": note_data["id"],
                    "workspace_id": DEMO_WORKSPACE_ID,
                    "project_id": proj_id,
                    "title": note_data["title"],
                    "content": json.dumps(note_data["content"]),
                    "owner_id": demo_user_id,
                    "is_pinned": note_data["is_pinned"],
                    "word_count": len(str(note_data["content"]).split()),
                    "reading_time_mins": max(1, len(str(note_data["content"]).split()) // 200),
                    "created_at": datetime.now() - timedelta(days=7 - notes_data.index(note_data)),
                },
            )
            note_ids[note_data["title"]] = note_data["id"]
        print(f"✅ Created {len(notes_data)} notes (2 pinned, 5 recent)")

        # ===================================================================
        # Create Issues Across Projects
        # ===================================================================
        issues_data = [
            # Authentication Project (8/12 issues complete)
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Setup Supabase Auth integration",
                "description": "Configure Supabase Auth for OAuth2 providers",
                "priority": "high",
                "sequence": 1,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Implement JWT token generation",
                "description": "Create access and refresh tokens with proper expiry",
                "priority": "high",
                "sequence": 2,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Add refresh token rotation",
                "description": "Implement automatic token rotation on refresh",
                "priority": "medium",
                "sequence": 3,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Create auth middleware",
                "description": "Middleware to verify JWT tokens on protected routes",
                "priority": "high",
                "sequence": 4,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Add Google OAuth2 provider",
                "description": "Integrate Google Sign-In",
                "priority": "medium",
                "sequence": 5,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Add GitHub OAuth2 provider",
                "description": "Integrate GitHub OAuth",
                "priority": "medium",
                "sequence": 6,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Implement rate limiting on auth endpoints",
                "description": "Prevent brute force attacks",
                "priority": "high",
                "sequence": 7,
            },
            {
                "project": "AUTH",
                "state": "Done",
                "name": "Add security headers",
                "description": "Configure CSP, CORS, etc.",
                "priority": "medium",
                "sequence": 8,
            },
            {
                "project": "AUTH",
                "state": "In Progress",
                "name": "Write E2E auth tests",
                "description": "Test complete auth flow with OAuth2",
                "priority": "high",
                "sequence": 9,
            },
            {
                "project": "AUTH",
                "state": "In Review",
                "name": "Security audit",
                "description": "Review auth implementation for vulnerabilities",
                "priority": "urgent",
                "sequence": 10,
            },
            {
                "project": "AUTH",
                "state": "Todo",
                "name": "Add biometric auth support",
                "description": "Support WebAuthn for passwordless login",
                "priority": "low",
                "sequence": 11,
            },
            {
                "project": "AUTH",
                "state": "Backlog",
                "name": "Implement SSO for enterprises",
                "description": "SAML integration for enterprise customers",
                "priority": "none",
                "sequence": 12,
            },
            # API Gateway Project (15/21 issues complete)
            {
                "project": "API",
                "state": "Done",
                "name": "Setup FastAPI project structure",
                "description": "Initialize FastAPI with proper folder structure",
                "priority": "high",
                "sequence": 1,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement workspace CRUD endpoints",
                "description": "REST endpoints for workspace management",
                "priority": "high",
                "sequence": 2,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement project CRUD endpoints",
                "description": "REST endpoints for project management",
                "priority": "high",
                "sequence": 3,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement issue CRUD endpoints",
                "description": "REST endpoints for issue tracking",
                "priority": "high",
                "sequence": 4,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement note CRUD endpoints",
                "description": "REST endpoints for note management",
                "priority": "high",
                "sequence": 5,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add pagination support",
                "description": "Implement cursor-based pagination",
                "priority": "medium",
                "sequence": 6,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add filtering and sorting",
                "description": "Query params for filtering and sorting",
                "priority": "medium",
                "sequence": 7,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement RLS policies",
                "description": "Row-level security for multi-tenancy",
                "priority": "high",
                "sequence": 8,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add API documentation",
                "description": "OpenAPI/Swagger docs with examples",
                "priority": "medium",
                "sequence": 9,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Setup error handling",
                "description": "RFC 7807 problem details format",
                "priority": "high",
                "sequence": 10,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add request validation",
                "description": "Pydantic v2 schemas for all endpoints",
                "priority": "high",
                "sequence": 11,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Implement rate limiting",
                "description": "Per-workspace rate limits",
                "priority": "high",
                "sequence": 12,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add health check endpoints",
                "description": "/health and /ready for k8s probes",
                "priority": "medium",
                "sequence": 13,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Setup logging and metrics",
                "description": "Structured logging with Prometheus metrics",
                "priority": "medium",
                "sequence": 14,
            },
            {
                "project": "API",
                "state": "Done",
                "name": "Add CORS configuration",
                "description": "Configure CORS for frontend origins",
                "priority": "high",
                "sequence": 15,
            },
            {
                "project": "API",
                "state": "In Progress",
                "name": "Implement GraphQL schema",
                "description": "Design GraphQL schema for complex queries",
                "priority": "medium",
                "sequence": 16,
            },
            {
                "project": "API",
                "state": "In Progress",
                "name": "Add GraphQL resolvers",
                "description": "Implement resolvers with DataLoader",
                "priority": "medium",
                "sequence": 17,
            },
            {
                "project": "API",
                "state": "In Review",
                "name": "Performance optimization",
                "description": "Profile and optimize slow endpoints",
                "priority": "high",
                "sequence": 18,
            },
            {
                "project": "API",
                "state": "Todo",
                "name": "Add caching layer",
                "description": "Redis caching for frequent queries",
                "priority": "medium",
                "sequence": 19,
            },
            {
                "project": "API",
                "state": "Todo",
                "name": "Implement webhooks",
                "description": "Allow clients to subscribe to events",
                "priority": "low",
                "sequence": 20,
            },
            {
                "project": "API",
                "state": "Backlog",
                "name": "Add API versioning strategy",
                "description": "Plan for API v2 with backward compatibility",
                "priority": "none",
                "sequence": 21,
            },
            # Frontend Project (10/18 issues complete)
            {
                "project": "FE",
                "state": "Done",
                "name": "Setup Next.js project",
                "description": "Initialize Next.js 14 with App Router",
                "priority": "high",
                "sequence": 1,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Configure TailwindCSS",
                "description": "Setup Tailwind with custom theme",
                "priority": "medium",
                "sequence": 2,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Add shadcn/ui components",
                "description": "Install base shadcn/ui component library",
                "priority": "medium",
                "sequence": 3,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Implement navigation sidebar",
                "description": "Left sidebar with workspace navigation",
                "priority": "high",
                "sequence": 4,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Create note list view",
                "description": "Display notes with filters and sorting",
                "priority": "high",
                "sequence": 5,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Create issue Kanban board",
                "description": "Drag-and-drop Kanban for issues",
                "priority": "high",
                "sequence": 6,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Create project list view",
                "description": "Project cards with progress metrics",
                "priority": "high",
                "sequence": 7,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Setup MobX stores",
                "description": "Create feature-based MobX stores",
                "priority": "high",
                "sequence": 8,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Integrate TanStack Query",
                "description": "Setup React Query for API calls",
                "priority": "high",
                "sequence": 9,
            },
            {
                "project": "FE",
                "state": "Done",
                "name": "Add authentication UI",
                "description": "Login/signup forms with OAuth buttons",
                "priority": "high",
                "sequence": 10,
            },
            {
                "project": "FE",
                "state": "In Progress",
                "name": "Implement TipTap editor",
                "description": "Rich text editor for notes",
                "priority": "high",
                "sequence": 11,
            },
            {
                "project": "FE",
                "state": "In Progress",
                "name": "Add ghost text feature",
                "description": "AI suggestions while typing",
                "priority": "medium",
                "sequence": 12,
            },
            {
                "project": "FE",
                "state": "In Review",
                "name": "Create margin annotations UI",
                "description": "Right sidebar for AI suggestions",
                "priority": "medium",
                "sequence": 13,
            },
            {
                "project": "FE",
                "state": "Todo",
                "name": "Implement search command palette",
                "description": "⌘K search across all content",
                "priority": "high",
                "sequence": 14,
            },
            {
                "project": "FE",
                "state": "Todo",
                "name": "Add dark mode support",
                "description": "Theme toggle with system preference",
                "priority": "medium",
                "sequence": 15,
            },
            {
                "project": "FE",
                "state": "Todo",
                "name": "Implement keyboard shortcuts",
                "description": "Vim-style shortcuts for power users",
                "priority": "low",
                "sequence": 16,
            },
            {
                "project": "FE",
                "state": "Backlog",
                "name": "Add mobile responsive design",
                "description": "Optimize for mobile devices",
                "priority": "none",
                "sequence": 17,
            },
            {
                "project": "FE",
                "state": "Backlog",
                "name": "Implement offline mode",
                "description": "Service worker for offline access",
                "priority": "none",
                "sequence": 18,
            },
        ]

        issue_ids = {}
        for issue in issues_data:
            issue_id = uuid.uuid4()
            proj_id = project_ids[issue["project"]]
            state_id = state_ids[issue["project"]][issue["state"]]

            await session.execute(
                text("""
                    INSERT INTO issues (id, workspace_id, project_id, state_id, name, description, sequence_id, priority, reporter_id, sort_order, created_at, updated_at, is_deleted)
                    VALUES (:id, :workspace_id, :project_id, :state_id, :name, :description, :sequence_id, :priority, :reporter_id, :sort_order, :created_at, NOW(), false)
                """),
                {
                    "id": issue_id,
                    "workspace_id": DEMO_WORKSPACE_ID,
                    "project_id": proj_id,
                    "state_id": state_id,
                    "name": issue["name"],
                    "description": issue["description"],
                    "sequence_id": issue["sequence"],
                    "priority": issue["priority"],
                    "reporter_id": demo_user_id,
                    "sort_order": issue["sequence"],
                    "created_at": datetime.now() - timedelta(days=30 - issue["sequence"]),
                },
            )
            issue_key = f"{issue['project']}-{issue['sequence']}"
            issue_ids[issue_key] = issue_id

        print(f"✅ Created {len(issues_data)} issues across 3 projects")
        print("   - AUTH: 12 issues (8 done, 1 in progress, 1 in review, 1 todo, 1 backlog)")
        print("   - API: 21 issues (15 done, 2 in progress, 1 in review, 2 todo, 1 backlog)")
        print("   - FE: 18 issues (10 done, 2 in progress, 1 in review, 3 todo, 2 backlog)")

        # ===================================================================
        # Migrate any old demo user data
        # ===================================================================
        old_demo_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        # Migrate AI sessions from old demo user ID to new auth user ID
        try:
            result = await session.execute(
                text("""
                    UPDATE ai_sessions SET user_id = :new_id
                    WHERE user_id = :old_id
                """),
                {"new_id": demo_user_id, "old_id": old_demo_user_id},
            )
            # Use getattr for type-safe access to rowcount
            migrated_count = getattr(result, "rowcount", 0)
            if migrated_count > 0:
                print(f"✅ Migrated {migrated_count} AI sessions to new user ID")
        except Exception:
            # Table might not exist in fresh installations
            pass

        await session.commit()


async def main() -> None:
    """Main seeding orchestration."""
    try:
        # Step 1: Create or get Supabase Auth user
        demo_user_id = await create_or_get_auth_user()

        # Step 2: Seed database with demo data
        await seed_database(demo_user_id)

        # Success summary
        print("\n" + "=" * 60)
        print("✅ DEMO DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📊 Summary:")
        print(f"   - User: Tin Dang ({DEMO_EMAIL})")
        print(f"   - Auth ID: {demo_user_id}")
        print(f"   - Workspace: pilot-space-demo ({DEMO_WORKSPACE_ID})")
        print("   - Projects: 3 (AUTH, API, FE)")
        print("   - Notes: 7 (2 pinned)")
        print("   - Issues: 51 across all states")
        print("   - Labels: 14")
        print("   - States: 18 (6 per project)")
        print("\n📝 Login credentials:")
        print(f"   - Email: {DEMO_EMAIL}")
        print(f"   - Password: {DEMO_PASSWORD}")
        print("\n🌐 URLs:")
        print("   - Frontend: http://localhost:3000/pilot-space-demo")
        print("   - Login: http://localhost:3000/login")
        print("   - API Docs: http://localhost:8000/docs")
        print("\n✨ You can now test all features with realistic data!\n")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
