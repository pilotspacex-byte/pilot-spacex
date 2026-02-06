"""Unit tests for role skill Pydantic schemas.

Tests validation rules, serialization, and computed fields.

Source: 011-role-based-skills, T015
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pilot_space.api.v1.schemas.role_skill import (
    CreateRoleSkillRequest,
    GenerateRoleSkillRequest,
    RegenerateRoleSkillRequest,
    RoleSkillResponse,
    RoleTemplateResponse,
    UpdateRoleSkillRequest,
)


class TestCreateRoleSkillRequest:
    """Tests for CreateRoleSkillRequest validation."""

    def test_valid_request(self) -> None:
        """Accept valid creation request."""
        req = CreateRoleSkillRequest(
            role_type="developer",
            role_name="Senior Developer",
            skill_content="# Developer\n\nSkill content here.",
        )
        assert req.role_type == "developer"
        assert req.is_primary is False

    def test_rejects_empty_role_name(self) -> None:
        """Reject empty role_name."""
        with pytest.raises(ValidationError):
            CreateRoleSkillRequest(
                role_type="developer",
                role_name="",
                skill_content="Content",
            )

    def test_rejects_long_role_name(self) -> None:
        """Reject role_name over 100 chars."""
        with pytest.raises(ValidationError):
            CreateRoleSkillRequest(
                role_type="developer",
                role_name="x" * 101,
                skill_content="Content",
            )

    def test_rejects_empty_skill_content(self) -> None:
        """Reject empty skill_content."""
        with pytest.raises(ValidationError):
            CreateRoleSkillRequest(
                role_type="developer",
                role_name="Dev",
                skill_content="",
            )

    def test_rejects_long_skill_content(self) -> None:
        """Reject skill_content over 15000 chars."""
        with pytest.raises(ValidationError):
            CreateRoleSkillRequest(
                role_type="developer",
                role_name="Dev",
                skill_content="x" * 15001,
            )

    def test_accepts_max_length_content(self) -> None:
        """Accept skill_content at exactly 15000 chars."""
        req = CreateRoleSkillRequest(
            role_type="developer",
            role_name="Dev",
            skill_content="x" * 15000,
        )
        assert len(req.skill_content) == 15000

    def test_camel_case_serialization(self) -> None:
        """Serialize to camelCase for frontend."""
        req = CreateRoleSkillRequest(
            role_type="developer",
            role_name="Dev",
            skill_content="Content",
            is_primary=True,
        )
        data = req.model_dump(by_alias=True)
        assert "roleType" in data
        assert "roleName" in data
        assert "skillContent" in data
        assert "isPrimary" in data


class TestUpdateRoleSkillRequest:
    """Tests for UpdateRoleSkillRequest validation."""

    def test_all_fields_optional(self) -> None:
        """Accept request with no fields (no-op update)."""
        req = UpdateRoleSkillRequest()
        assert req.role_name is None
        assert req.skill_content is None
        assert req.is_primary is None

    def test_partial_update(self) -> None:
        """Accept partial update with only role_name."""
        req = UpdateRoleSkillRequest(role_name="Updated Name")
        assert req.role_name == "Updated Name"
        assert req.skill_content is None


class TestGenerateRoleSkillRequest:
    """Tests for GenerateRoleSkillRequest validation."""

    def test_valid_request(self) -> None:
        """Accept valid generation request."""
        req = GenerateRoleSkillRequest(
            role_type="developer",
            experience_description="5 years Python backend development",
        )
        assert req.role_type == "developer"
        assert req.role_name is None

    def test_rejects_short_experience(self) -> None:
        """Reject experience_description under 10 chars."""
        with pytest.raises(ValidationError):
            GenerateRoleSkillRequest(
                role_type="developer",
                experience_description="short",
            )

    def test_strips_whitespace_from_experience(self) -> None:
        """Strip whitespace from experience_description."""
        req = GenerateRoleSkillRequest(
            role_type="developer",
            experience_description="   5 years Python backend dev   ",
        )
        assert req.experience_description == "5 years Python backend dev"

    def test_accepts_optional_role_name(self) -> None:
        """Accept optional role_name for generation."""
        req = GenerateRoleSkillRequest(
            role_type="developer",
            experience_description="Senior backend developer",
            role_name="Lead Engineer",
        )
        assert req.role_name == "Lead Engineer"


class TestRegenerateRoleSkillRequest:
    """Tests for RegenerateRoleSkillRequest validation."""

    def test_rejects_short_experience(self) -> None:
        """Reject experience_description under 10 chars."""
        with pytest.raises(ValidationError):
            RegenerateRoleSkillRequest(experience_description="tiny")


class TestRoleTemplateResponse:
    """Tests for RoleTemplateResponse serialization."""

    def test_serializes_correctly(self) -> None:
        """Serialize template response to camelCase."""
        resp = RoleTemplateResponse(
            id=uuid4(),
            role_type="developer",
            display_name="Developer",
            description="Code quality",
            icon="Code",
            sort_order=1,
            version=1,
            default_skill_content="# Developer",
        )
        data = resp.model_dump(by_alias=True)
        assert "roleType" in data
        assert "displayName" in data
        assert "defaultSkillContent" in data
        assert "sortOrder" in data


class TestRoleSkillResponse:
    """Tests for RoleSkillResponse serialization."""

    def test_includes_computed_fields(self) -> None:
        """Response includes template_update_available and word_count."""
        now = datetime.now(tz=UTC)
        resp = RoleSkillResponse(
            id=uuid4(),
            role_type="developer",
            role_name="Senior Dev",
            skill_content="hello world test content",
            is_primary=True,
            template_version=1,
            template_update_available=True,
            word_count=4,
            created_at=now,
            updated_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert data["templateUpdateAvailable"] is True
        assert data["wordCount"] == 4

    def test_camel_case_output(self) -> None:
        """All fields serialize to camelCase."""
        now = datetime.now(tz=UTC)
        resp = RoleSkillResponse(
            id=uuid4(),
            role_type="developer",
            role_name="Dev",
            skill_content="Content",
            is_primary=False,
            word_count=1,
            created_at=now,
            updated_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert "roleType" in data
        assert "roleName" in data
        assert "skillContent" in data
        assert "isPrimary" in data
        assert "experienceDescription" in data
        assert "templateVersion" in data
