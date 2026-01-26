#!/usr/bin/env python3
"""
Mock SDLC Test: Note -> Issues -> Sprint/Cycle

Tests the full workflow from Note-First to issue tracking.
Uses direct database operations to bypass API auth for testing.
"""

import asyncio

# Add parent path for imports
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, "/Users/tindang/workspaces/tind-repo/pilot-space/backend/src")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pilot_space.infrastructure.database.models.cycle import Cycle, CycleStatus
from pilot_space.infrastructure.database.models.issue import Issue, IssuePriority

# Import models
from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.note_issue_link import NoteIssueLink, NoteLinkType
from pilot_space.infrastructure.database.models.project import Project
from pilot_space.infrastructure.database.models.state import State

# Database URL
DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:54322/pilot_space"  # pragma: allowlist secret
)

# Test data IDs
WORKSPACE_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
PROJECT_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("e1dfcbff-0ffc-48d1-ae96-aed53be333c5")


async def main():
    """Run the SDLC flow test."""
    print("\n" + "=" * 50)
    print("  SDLC Flow Test: Note → Issues → Sprint")
    print("=" * 50)

    # Create engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Get default state (Backlog)
        result = await session.execute(
            select(State).where(
                State.workspace_id == WORKSPACE_ID,
                State.name == "Backlog",
                State.is_deleted.is_(False),
            )
        )
        backlog_state = result.scalar_one_or_none()
        if not backlog_state:
            print("❌ Error: Backlog state not found")
            return

        print(f"\n✓ Found Backlog state: {backlog_state.id}")

        # Get project for sequence ID
        result = await session.execute(select(Project).where(Project.id == PROJECT_ID))
        project = result.scalar_one_or_none()
        if not project:
            print("❌ Error: Project not found")
            return

        print(f"✓ Found project: {project.name} ({project.identifier})")

        # Step 1: Create a Note with planning content
        print("\n--- Step 1: Creating Note with planning content ---")

        note_content = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [
                        {"type": "text", "text": "Sprint Planning - Authentication Module"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Key tasks for this sprint:"}],
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Implement JWT token generation - HIGH priority",
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Add password reset flow with email",
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Create login rate limiting - URGENT security fix",
                                        }
                                    ],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "Add OAuth2 integration (Google, GitHub)",
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Bug: Session expires too quickly - users logged out after 5 minutes.",
                        }
                    ],
                },
            ],
        }

        note = Note(
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            title="Sprint Planning - Authentication Module",
            content=note_content,
            owner_id=USER_ID,
        )
        session.add(note)
        await session.flush()
        print(f"✓ Created Note: {note.id}")
        print(f"  Title: {note.title}")

        # Step 2: Mock AI Issue Extraction
        print("\n--- Step 2: Mock AI Issue Extraction ---")
        print("  (In production, this would call Claude AI)")

        mock_extracted_issues = [
            {
                "title": "Implement JWT token generation and validation",
                "description": "Create JWT token service with token generation, validation, and refresh logic.",
                "priority": IssuePriority.HIGH,
                "labels": ["auth", "security", "backend"],
                "confidence": 0.95,
            },
            {
                "title": "Add password reset flow with email verification",
                "description": "Implement password reset with token generation and email template.",
                "priority": IssuePriority.MEDIUM,
                "labels": ["auth", "email", "backend"],
                "confidence": 0.88,
            },
            {
                "title": "Create login rate limiting for security",
                "description": "Security: Implement rate limiting for login attempts to prevent brute force attacks.",
                "priority": IssuePriority.URGENT,
                "labels": ["auth", "security", "urgent"],
                "confidence": 0.92,
            },
            {
                "title": "Add OAuth2 integration for Google and GitHub",
                "description": "Implement social login with Google and GitHub OAuth2.",
                "priority": IssuePriority.MEDIUM,
                "labels": ["auth", "oauth", "backend"],
                "confidence": 0.85,
            },
            {
                "title": "Fix session expiring too quickly",
                "description": "Bug: Users are being logged out after 5 minutes. Investigate token expiry settings.",
                "priority": IssuePriority.HIGH,
                "labels": ["bug", "auth"],
                "confidence": 0.90,
            },
        ]

        print(f"\n  AI Extracted {len(mock_extracted_issues)} issues:")
        for i, issue in enumerate(mock_extracted_issues, 1):
            print(f"    {i}. [{issue['priority'].value.upper()}] {issue['title']}")
            print(f"       Confidence: {issue['confidence'] * 100:.0f}%")

        # Step 3: Create Issues from Mock Extracted Data
        print("\n--- Step 3: Creating Issues from AI suggestions ---")

        # Get max sequence_id for project
        result = await session.execute(
            select(Issue.sequence_id)
            .where(Issue.project_id == PROJECT_ID)
            .order_by(Issue.sequence_id.desc())
            .limit(1)
        )
        max_seq = result.scalar() or 0

        created_issues = []
        for _i, issue_data in enumerate(mock_extracted_issues, 1):
            max_seq += 1
            issue = Issue(
                workspace_id=WORKSPACE_ID,
                project_id=PROJECT_ID,
                sequence_id=max_seq,
                name=issue_data["title"],
                description=issue_data["description"],
                priority=issue_data["priority"],
                state_id=backlog_state.id,
                reporter_id=USER_ID,
                ai_metadata={
                    "extracted_from_note": str(note.id),
                    "confidence": issue_data["confidence"],
                    "suggested_labels": issue_data["labels"],
                },
            )
            session.add(issue)
            await session.flush()
            created_issues.append(issue)
            print(f"  ✓ Created: {project.identifier}-{issue.sequence_id} - {issue.name[:40]}...")

        # Create note-issue links
        print("\n  Creating Note-Issue links...")
        for issue in created_issues:
            link = NoteIssueLink(
                workspace_id=WORKSPACE_ID,
                note_id=note.id,
                issue_id=issue.id,
                link_type=NoteLinkType.EXTRACTED,
            )
            session.add(link)
        await session.flush()
        print(f"  ✓ Linked {len(created_issues)} issues to note")

        # Step 4: Create a Sprint/Cycle
        print("\n--- Step 4: Creating Sprint/Cycle ---")

        cycle = Cycle(
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            name="Sprint 1 - Authentication",
            description="Complete the authentication module with JWT, OAuth, and security features",
            status=CycleStatus.PLANNED,
            start_date=datetime.now(UTC).date(),
            end_date=datetime.now(UTC).date() + timedelta(days=14),
            sequence=1,
            owned_by_id=USER_ID,
        )
        session.add(cycle)
        await session.flush()
        print(f"  ✓ Created Cycle: {cycle.id}")
        print(f"    Name: {cycle.name}")
        print(f"    Status: {cycle.status.value}")
        print(f"    Duration: {cycle.start_date} to {cycle.end_date}")

        # Step 5: Add Issues to Cycle
        print("\n--- Step 5: Adding issues to Sprint ---")

        for issue in created_issues:
            issue.cycle_id = cycle.id
            print(f"  ✓ Added {project.identifier}-{issue.sequence_id} to {cycle.name}")

        # Commit all changes
        await session.commit()

        # Summary
        print("\n" + "=" * 50)
        print("  SDLC Flow Test Complete!")
        print("=" * 50)

        print("\n✓ Summary:")
        print(f"  • Created Note: {note.title}")
        print(f"  • AI extracted: {len(mock_extracted_issues)} issues")
        print(f"  • Created issues: {len(created_issues)}")
        print(f"  • Created Sprint: {cycle.name}")
        print(f"  • Assigned to Sprint: {len(created_issues)} issues")

        print("\n✓ Flow Demonstrated:")
        print("  Note Canvas → AI Issue Extraction → Issue Tracker → Sprint Planning")

        print("\n✓ View in UI:")
        print("  • Notes: http://localhost:3000/pilot-space-demo/notes")
        print("  • Issues: http://localhost:3000/pilot-space-demo/issues")
        print(
            f"  • Issue Detail: http://localhost:3000/pilot-space-demo/issues/{created_issues[0].id}"
        )

        # Show created issue IDs
        print("\n✓ Created Issue IDs:")
        for issue in created_issues:
            print(f"  • {project.identifier}-{issue.sequence_id}: {issue.id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
