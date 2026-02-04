"""Create Supabase Auth user for demo account.

This script creates a Supabase Auth user that matches the demo database user
created by seed_demo.py, enabling authentication for the demo account.

Requirements:
- Supabase local instance running (docker compose up)
- SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment
"""

import asyncio
import os
import sys
import uuid

import httpx

# Demo user credentials (must match seed_demo.py)
DEMO_USER_ID = uuid.UUID("77a6813e-0aa3-400c-8d4e-540b6ed2187a")
DEMO_EMAIL = "test@pilot.space"
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "DemoPassword123!")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:18000")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


async def create_auth_user() -> None:
    """Create Supabase Auth user via Admin API."""
    if not SUPABASE_SERVICE_KEY:
        print("❌ ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable not set")
        print("   Set it in backend/.env or run: export SUPABASE_SERVICE_ROLE_KEY=<key>")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🔐 CREATING SUPABASE AUTH USER FOR DEMO")
    print("=" * 60 + "\n")

    print(f"📧 Email: {DEMO_EMAIL}")
    print(f"🔑 Password: {DEMO_PASSWORD}")
    print(f"🆔 User ID: {DEMO_USER_ID}")
    print(f"🌐 Supabase URL: {SUPABASE_URL}")
    print()

    # Supabase Auth Admin API endpoint
    auth_admin_url = f"{SUPABASE_URL}/auth/v1/admin/users"

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "full_name": "Tin Dang",
        },
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
                    print(f"⚠️  Auth user already exists: {existing_user['id']}")
                    print("   To recreate, delete via Supabase Studio or use auth admin API")
                    return

            # Create new auth user
            print("🚀 Creating new auth user...")
            response = await client.post(
                auth_admin_url,
                headers=headers,
                json=payload,
                timeout=10.0,
            )

            if response.status_code in (200, 201):
                user_data = response.json()
                print("\n✅ SUCCESS! Auth user created:")
                print(f"   - Auth ID: {user_data['id']}")
                print(f"   - Email: {user_data['email']}")
                print(f"   - Confirmed: {user_data['email_confirmed_at'] is not None}")
                print("\n📝 Login credentials:")
                print(f"   - Email: {DEMO_EMAIL}")
                print(f"   - Password: {DEMO_PASSWORD}")
                print("\n🌐 Login URL: http://localhost:3000/login")
                print(
                    f"\n⚠️  NOTE: Auth user ID ({user_data['id']}) differs from database user ID ({DEMO_USER_ID})"
                )
                print("   This is expected - Supabase Auth generates its own UUIDs.")
                print("   Update your CurrentUserId dependency to link these if needed.")
            else:
                print("\n❌ ERROR: Failed to create auth user")
                print(f"   Status: {response.status_code}")
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


if __name__ == "__main__":
    asyncio.run(create_auth_user())
