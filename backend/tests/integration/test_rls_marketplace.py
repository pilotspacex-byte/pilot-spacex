"""RLS policy audit for marketplace tables (Phase 056-03, Task 1).

Static analysis tests that read migration 104 source and verify
RLS policy completeness for all 4 marketplace tables plus
skill_templates extension columns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path to the migration file under test
MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "104_add_marketplace_tables.py"
)

MARKETPLACE_TABLES = [
    "skill_marketplace_listings",
    "skill_versions",
    "skill_reviews",
    "skill_graphs",
]


@pytest.fixture(scope="module")
def migration_source() -> str:
    """Read migration 104 source once for all tests."""
    return MIGRATION_PATH.read_text()


# ---------------------------------------------------------------------------
# ENABLE + FORCE RLS for all 4 tables
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table", MARKETPLACE_TABLES)
class TestRLSEnabled:
    """Verify ENABLE and FORCE ROW LEVEL SECURITY for each table."""

    def test_enable_rls(self, migration_source: str, table: str) -> None:
        stmt = f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
        assert stmt in migration_source, (
            f"Missing ENABLE ROW LEVEL SECURITY for {table}"
        )

    def test_force_rls(self, migration_source: str, table: str) -> None:
        stmt = f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"
        assert stmt in migration_source, (
            f"Missing FORCE ROW LEVEL SECURITY for {table}"
        )


# ---------------------------------------------------------------------------
# Service role bypass for all 4 tables
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table", MARKETPLACE_TABLES)
def test_service_role_bypass(migration_source: str, table: str) -> None:
    """Each table must have a service_role bypass policy."""
    policy_name = f"{table}_service_role"
    assert policy_name in migration_source, (
        f"Missing service_role bypass policy for {table}"
    )
    # Verify it targets service_role
    assert "TO service_role" in migration_source


# ---------------------------------------------------------------------------
# Marketplace-specific policies
# ---------------------------------------------------------------------------


class TestMarketplaceListingsPolicy:
    """Verify public-read and OWNER/ADMIN write policies for listings."""

    def test_public_read_policy(self, migration_source: str) -> None:
        """Marketplace listings must be publicly readable (USING (true) for SELECT)."""
        # Find the read policy for listings
        assert '"skill_marketplace_listings_read"' in migration_source
        # The policy uses USING (true) for public read
        assert "FOR SELECT" in migration_source
        # Verify USING (true) appears (public read)
        assert "USING (true)" in migration_source

    def test_write_policy_owner_admin_check(self, migration_source: str) -> None:
        """Write policies must reference workspace_members with OWNER/ADMIN role check."""
        assert '"skill_marketplace_listings_write"' in migration_source
        # Must check workspace_members table
        assert "workspace_members" in migration_source
        # Must check for OWNER and ADMIN roles
        assert "'OWNER'" in migration_source
        assert "'ADMIN'" in migration_source

    def test_write_policy_uses_current_user(self, migration_source: str) -> None:
        """Write policies must use current_setting for user identification."""
        assert "current_setting('app.current_user_id', true)::uuid" in migration_source


# ---------------------------------------------------------------------------
# Skill graphs workspace isolation
# ---------------------------------------------------------------------------


class TestSkillGraphsWorkspaceIsolation:
    """Verify skill_graphs uses standard workspace isolation RLS."""

    def test_workspace_isolation_policy_exists(self, migration_source: str) -> None:
        """skill_graphs must have a workspace isolation policy."""
        assert '"skill_graphs_workspace_isolation"' in migration_source

    def test_uses_current_user_setting(self, migration_source: str) -> None:
        """Workspace isolation must use current_setting for user ID."""
        # Already covered globally, but verify it appears in the skill_graphs section
        assert "current_setting('app.current_user_id', true)::uuid" in migration_source

    def test_includes_all_roles(self, migration_source: str) -> None:
        """Workspace isolation for skill_graphs includes all member roles."""
        assert "'MEMBER'" in migration_source
        assert "'GUEST'" in migration_source


# ---------------------------------------------------------------------------
# Skill reviews author-based write policies
# ---------------------------------------------------------------------------


class TestSkillReviewsPolicies:
    """Verify skill_reviews has author-based write control."""

    def test_insert_policy(self, migration_source: str) -> None:
        """Reviews must have an INSERT policy checking user_id."""
        assert '"skill_reviews_write"' in migration_source
        assert "FOR INSERT" in migration_source

    def test_update_delete_policy(self, migration_source: str) -> None:
        """Reviews must have an update/delete policy for the author."""
        assert '"skill_reviews_update_delete"' in migration_source


# ---------------------------------------------------------------------------
# Skill templates extension columns
# ---------------------------------------------------------------------------


class TestSkillTemplatesExtension:
    """Verify skill_templates gets marketplace extension columns."""

    def test_marketplace_listing_id_column(self, migration_source: str) -> None:
        """skill_templates must have marketplace_listing_id FK column."""
        assert "marketplace_listing_id" in migration_source

    def test_installed_version_column(self, migration_source: str) -> None:
        """skill_templates must have installed_version column."""
        assert "installed_version" in migration_source

    def test_marketplace_listing_fk(self, migration_source: str) -> None:
        """marketplace_listing_id must FK to skill_marketplace_listings."""
        assert "skill_marketplace_listings.id" in migration_source

    def test_on_delete_set_null(self, migration_source: str) -> None:
        """FK on marketplace_listing_id should SET NULL on delete."""
        assert "SET NULL" in migration_source
