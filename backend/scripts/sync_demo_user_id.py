"""Sync database user ID with Supabase Auth user ID.

This script updates the demo database user ID to match the Supabase Auth user ID,
enabling proper authentication flow for the demo account.

Run this AFTER creating the Supabase Auth user via create_demo_auth_user.py.
"""

import asyncio
import os
import sys
import uuid

import httpx
from sqlalchemy import text

from pilot_space.infrastructure.database.engine import get_db_session

# Demo user credentials
DEMO_EMAIL = "tin@pilot-space.dev"
OLD_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:18000")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


async def get_auth_user_id() -> uuid.UUID | None:
    """Get Supabase Auth user ID for demo email.

    Returns:
        Auth user UUID if found, None otherwise.
    """
    if not SUPABASE_SERVICE_KEY:
        print("❌ ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable not set")
        sys.exit(1)

    auth_admin_url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(auth_admin_url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                users = response.json().get("users", [])
                demo_user = next((u for u in users if u.get("email") == DEMO_EMAIL), None)

                if demo_user:
                    return uuid.UUID(demo_user["id"])
                print(f"❌ ERROR: No auth user found with email: {DEMO_EMAIL}")
                print("   Run create_demo_auth_user.py first!")
                sys.exit(1)
            else:
                print(f"❌ ERROR: Failed to list auth users: {response.status_code}")
                sys.exit(1)

        except Exception as e:
            print(f"❌ ERROR: {e}")
            sys.exit(1)


async def sync_user_id() -> None:
    """Sync database user ID with Supabase Auth user ID."""
    print("\n" + "=" * 60)
    print("🔄 SYNCING DATABASE USER ID WITH SUPABASE AUTH")
    print("=" * 60 + "\n")

    # Get Auth user ID
    print("🔍 Fetching Supabase Auth user ID...")
    auth_user_id = await get_auth_user_id()
    print(f"✅ Found auth user ID: {auth_user_id}\n")

    # Update database
    async with get_db_session() as session:
        # Check if database user exists
        result = await session.execute(
            text("SELECT id, email FROM users WHERE id = :old_id OR email = :email"),
            {"old_id": OLD_USER_ID, "email": DEMO_EMAIL},
        )
        db_user = result.fetchone()

        if not db_user:
            print(f"❌ ERROR: No database user found with ID {OLD_USER_ID} or email {DEMO_EMAIL}")
            print("   Run seed_demo.py first!")
            sys.exit(1)

        current_db_id = db_user[0]
        print(f"📊 Current database user ID: {current_db_id}")
        print(f"🎯 Target auth user ID: {auth_user_id}")

        if current_db_id == auth_user_id:
            print("\n✅ User IDs already match! No sync needed.")
            return

        # Update user ID across all related tables
        print(f"\n🔄 Updating user ID from {current_db_id} to {auth_user_id}...")
        print("⚠️  This will update multiple tables with foreign key relationships\n")

        try:
            # First, temporarily change old user's email to avoid unique constraint
            print("1️⃣  Temporarily changing old user's email...")
            await session.execute(
                text("UPDATE users SET email = :temp_email WHERE id = :old_id"),
                {"temp_email": f"old_{DEMO_EMAIL}", "old_id": current_db_id},
            )

            # Create a new user record with the auth ID (clone of old user)
            print("2️⃣  Creating new user record with auth ID...")
            await session.execute(
                text("""
                    INSERT INTO users (id, email, full_name, avatar_url, created_at, updated_at, is_deleted)
                    VALUES (:new_id, :email, :full_name, :avatar_url, NOW(), NOW(), false)
                """),
                {
                    "new_id": auth_user_id,
                    "email": DEMO_EMAIL,
                    "full_name": "Tin Dang",
                    "avatar_url": None,
                },
            )

            # 3. Update workspace members
            print("3️⃣  Updating workspace_members...")
            await session.execute(
                text("UPDATE workspace_members SET user_id = :new_id WHERE user_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )

            # 4. Update issues (reporter_id, assignee_id)
            print("4️⃣  Updating issues...")
            await session.execute(
                text("UPDATE issues SET reporter_id = :new_id WHERE reporter_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )
            await session.execute(
                text("UPDATE issues SET assignee_id = :new_id WHERE assignee_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )

            # 5. Update notes
            print("5️⃣  Updating notes...")
            await session.execute(
                text("UPDATE notes SET owner_id = :new_id WHERE owner_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )

            # 6. Update projects (lead_id)
            print("6️⃣  Updating projects...")
            await session.execute(
                text("UPDATE projects SET lead_id = :new_id WHERE lead_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )

            # 7. Update workspaces (owner_id)
            print("7️⃣  Updating workspaces...")
            await session.execute(
                text("UPDATE workspaces SET owner_id = :new_id WHERE owner_id = :old_id"),
                {"new_id": auth_user_id, "old_id": current_db_id},
            )

            # 8. Delete old user record
            print("8️⃣  Deleting old user record...")
            await session.execute(
                text("DELETE FROM users WHERE id = :old_id"),
                {"old_id": current_db_id},
            )

            await session.commit()

            print("\n✅ Successfully updated user ID across all tables!")
            print("\n📝 Updated records:")
            print(f"   - users: {current_db_id} → {auth_user_id}")
            print("   - workspace_members: updated")
            print("   - issues: updated")
            print("   - notes: updated")
            print("   - projects: updated")
            print("   - workspaces: updated")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ ERROR: Failed to update user ID: {e}")
            print("\nPossible causes:")
            print("   - Foreign key constraints")
            print("   - Database migrations not applied")
            print("   - User ID already exists")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ USER ID SYNC COMPLETE!")
    print("=" * 60)
    print("\n🌐 You can now login at: http://localhost:3000/login")
    print(f"📧 Email: {DEMO_EMAIL}")
    print("🔑 Password: DemoPassword123!")
    print("\n🎉 All systems ready for demo!\n")


if __name__ == "__main__":
    asyncio.run(sync_user_id())
