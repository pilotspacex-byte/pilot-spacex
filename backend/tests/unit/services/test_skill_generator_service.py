"""Tests for SkillGeneratorService — conversational skill generation.

Phase 051, Plan 01: Multi-turn skill generation, iteration, save, and metadata inference.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.skill.skill_generator_service import (
    SkillGeneratorPayload,
    SkillGeneratorResult,
    SkillGeneratorService,
    SkillSavePayload,
    SkillSaveResult,
)
from pilot_space.domain.exceptions import ForbiddenError
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceRole

_WORKSPACE_ID = uuid4()
_USER_ID = uuid4()
_SESSION_ID = uuid4()


def _make_llm_response(data: dict) -> MagicMock:
    """Create a mock LLMResponse with text attribute."""
    resp = MagicMock()
    resp.text = json.dumps(data)
    resp.model = "claude-sonnet-4-20250514"
    return resp


def _base_llm_data(*, is_complete: bool = False) -> dict:
    """Standard LLM JSON response fields."""
    return {
        "name": "Code Reviewer",
        "description": "Reviews pull requests for quality",
        "category": "engineering",
        "icon": "GitPullRequest",
        "skill_content": "# Code Reviewer\n\nReview PRs for quality and best practices.",
        "example_prompts": ["Review this PR", "Check code quality"],
        "context_requirements": ["Pull request diff", "Repository context"],
        "tool_declarations": ["read_file", "create_comment"],
        "graph_data": {
            "nodes": [
                {"id": "1", "type": "prompt", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}
            ],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        },
        "is_complete": is_complete,
        "refinement_suggestion": None if is_complete else "Would you like to add error handling patterns?",
    }


def _mock_role_result(role: WorkspaceRole) -> MagicMock:
    """Create a mock execute result that returns a role from .scalar()."""
    result = MagicMock()
    result.scalar.return_value = role
    return result


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_llm_gateway() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock, mock_llm_gateway: AsyncMock) -> SkillGeneratorService:
    return SkillGeneratorService(session=mock_session, llm_gateway=mock_llm_gateway)


# ---------------------------------------------------------------------------
# generate_turn tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_turn_first_turn_not_complete(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """Turn 1 returns is_complete=False and a refinement_suggestion."""
    llm_data = _base_llm_data(is_complete=False)
    mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

    payload = SkillGeneratorPayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        message="Create a skill that reviews pull requests",
        turn_number=1,
        current_draft=None,
    )

    result = await service.generate_turn(payload)

    assert isinstance(result, SkillGeneratorResult)
    assert result.is_complete is False
    assert result.refinement_suggestion is not None
    assert result.name == "Code Reviewer"
    assert result.skill_content  # non-empty
    mock_llm_gateway.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_turn_third_turn_complete(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """Turn 3+ returns is_complete=True with full skill_content."""
    llm_data = _base_llm_data(is_complete=True)
    mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

    payload = SkillGeneratorPayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        message="Looks good, finalize it",
        turn_number=3,
        current_draft={"name": "Code Reviewer", "skill_content": "# Code Reviewer"},
    )

    result = await service.generate_turn(payload)

    assert result.is_complete is True
    assert result.skill_content
    assert result.name == "Code Reviewer"


@pytest.mark.asyncio
async def test_generate_turn_updates_existing_draft(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """When current_draft is provided, the refinement prompt is used."""
    llm_data = _base_llm_data(is_complete=False)
    mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

    existing_draft = {"name": "Code Reviewer", "skill_content": "# Code Reviewer v1"}
    payload = SkillGeneratorPayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        message="Add error handling patterns",
        turn_number=2,
        current_draft=existing_draft,
    )

    result = await service.generate_turn(payload)

    assert isinstance(result, SkillGeneratorResult)
    # Verify LLM was called with the current draft context
    call_kwargs = mock_llm_gateway.complete.call_args
    assert call_kwargs is not None


@pytest.mark.asyncio
async def test_generate_turn_session_data_format(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """Session data has mode, turn_count, draft, iteration_history, status."""
    llm_data = _base_llm_data(is_complete=False)
    mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

    payload = SkillGeneratorPayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        message="Create a skill for code review",
        turn_number=1,
        current_draft=None,
    )

    result = await service.generate_turn(payload)
    sd = result.session_data

    assert sd["mode"] == "skill_generation"
    assert sd["turn_count"] == 1
    assert "draft" in sd
    assert isinstance(sd["iteration_history"], list)
    assert sd["status"] == "gathering"


@pytest.mark.asyncio
async def test_generate_turn_status_transitions(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """Status transitions: turn 1=gathering, turn 2=refining, turn 3+=preview."""
    for turn, expected_status in [(1, "gathering"), (2, "refining"), (3, "preview"), (5, "preview")]:
        llm_data = _base_llm_data(is_complete=(turn >= 3))
        mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

        payload = SkillGeneratorPayload(
            workspace_id=_WORKSPACE_ID,
            user_id=_USER_ID,
            session_id=_SESSION_ID,
            message="test message",
            turn_number=turn,
            current_draft={"name": "test"} if turn > 1 else None,
        )
        result = await service.generate_turn(payload)
        assert result.session_data["status"] == expected_status, f"Turn {turn} expected {expected_status}"


@pytest.mark.asyncio
async def test_metadata_extraction(
    service: SkillGeneratorService,
    mock_llm_gateway: AsyncMock,
) -> None:
    """Generated result includes example_prompts, context_requirements, tool_declarations."""
    llm_data = _base_llm_data(is_complete=True)
    mock_llm_gateway.complete.return_value = _make_llm_response(llm_data)

    payload = SkillGeneratorPayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        message="Finalize it",
        turn_number=3,
        current_draft={"name": "Code Reviewer"},
    )

    result = await service.generate_turn(payload)

    assert isinstance(result.example_prompts, list)
    assert len(result.example_prompts) > 0
    assert isinstance(result.context_requirements, list)
    assert len(result.context_requirements) > 0
    assert isinstance(result.tool_declarations, list)
    assert len(result.tool_declarations) > 0


# ---------------------------------------------------------------------------
# save_skill tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_skill_personal(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """save_type='personal' creates a UserSkill record."""
    payload = SkillSavePayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        save_type="personal",
        name="Code Reviewer",
        description="Reviews PRs",
        category="engineering",
        icon="GitPullRequest",
        skill_content="# Code Reviewer\n\nReview PRs.",
        example_prompts=["Review this PR"],
        graph_data=None,
    )

    result = await service.save_skill(payload)

    assert isinstance(result, SkillSaveResult)
    assert result.skill_name == "Code Reviewer"
    assert result.save_type == "personal"
    assert result.skill_id is not None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    # Verify UserSkill was created
    added_obj = mock_session.add.call_args[0][0]
    from pilot_space.infrastructure.database.models.user_skill import UserSkill

    assert isinstance(added_obj, UserSkill)
    assert added_obj.user_id == _USER_ID
    assert added_obj.skill_name == "Code Reviewer"
    assert added_obj.is_active is True


@pytest.mark.asyncio
async def test_save_skill_workspace(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """save_type='workspace' creates a SkillTemplate with source='workspace'."""
    # Mock role query to return ADMIN so save proceeds
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.ADMIN))

    payload = SkillSavePayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        save_type="workspace",
        name="Code Reviewer",
        description="Reviews PRs",
        category="engineering",
        icon="GitPullRequest",
        skill_content="# Code Reviewer\n\nReview PRs.",
        example_prompts=["Review this PR"],
        graph_data=None,
    )

    result = await service.save_skill(payload)

    assert isinstance(result, SkillSaveResult)
    assert result.save_type == "workspace"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    added_obj = mock_session.add.call_args[0][0]
    from pilot_space.infrastructure.database.models.skill_template import SkillTemplate

    assert isinstance(added_obj, SkillTemplate)
    assert added_obj.source == "workspace"
    assert added_obj.created_by == _USER_ID


@pytest.mark.asyncio
async def test_save_skill_workspace_with_graph(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """save_type='workspace' with graph_data creates SkillGraph linked to template."""
    # Mock role query to return ADMIN so save proceeds
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.ADMIN))

    graph_data = {
        "nodes": [
            {"id": "1", "type": "prompt", "position": {"x": 0, "y": 0}, "data": {"label": "Step 1"}}
        ],
        "edges": [{"id": "e1-2", "source": "1", "target": "2"}],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }

    payload = SkillSavePayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        save_type="workspace",
        name="Code Reviewer",
        description="Reviews PRs",
        category="engineering",
        icon="GitPullRequest",
        skill_content="# Code Reviewer\n\nReview PRs.",
        example_prompts=["Review this PR"],
        graph_data=graph_data,
    )

    result = await service.save_skill(payload)

    assert result.save_type == "workspace"
    # Should have added SkillTemplate + SkillGraph = 2 add() calls
    assert mock_session.add.call_count == 2
    assert mock_session.flush.await_count == 2

    # Second add should be SkillGraph
    second_add = mock_session.add.call_args_list[1][0][0]
    from pilot_space.infrastructure.database.models.skill_graph import SkillGraph

    assert isinstance(second_add, SkillGraph)
    assert second_add.graph_json == graph_data
    assert second_add.node_count == 1
    assert second_add.edge_count == 1


# ---------------------------------------------------------------------------
# Admin role enforcement tests (SKG-05)
# ---------------------------------------------------------------------------


def _workspace_save_payload() -> SkillSavePayload:
    """Reusable workspace save payload for role tests."""
    return SkillSavePayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        save_type="workspace",
        name="Test Skill",
        description="desc",
        category="general",
        icon="Wand2",
        skill_content="# Test\n\nContent.",
        example_prompts=["test"],
        graph_data=None,
    )


@pytest.mark.asyncio
async def test_save_skill_workspace_forbidden_for_member(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """MEMBER role cannot save workspace skills — raises ForbiddenError."""
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.MEMBER))

    with pytest.raises(ForbiddenError, match="Admin or owner role required"):
        await service.save_skill(_workspace_save_payload())


@pytest.mark.asyncio
async def test_save_skill_workspace_forbidden_for_guest(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """GUEST role cannot save workspace skills — raises ForbiddenError."""
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.GUEST))

    with pytest.raises(ForbiddenError, match="Admin or owner role required"):
        await service.save_skill(_workspace_save_payload())


@pytest.mark.asyncio
async def test_save_skill_workspace_allowed_for_admin(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """ADMIN role can save workspace skills successfully."""
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.ADMIN))

    result = await service.save_skill(_workspace_save_payload())

    assert isinstance(result, SkillSaveResult)
    assert result.save_type == "workspace"
    assert result.skill_name == "Test Skill"


@pytest.mark.asyncio
async def test_save_skill_workspace_allowed_for_owner(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """OWNER role can save workspace skills successfully."""
    mock_session.execute = AsyncMock(return_value=_mock_role_result(WorkspaceRole.OWNER))

    result = await service.save_skill(_workspace_save_payload())

    assert isinstance(result, SkillSaveResult)
    assert result.save_type == "workspace"


@pytest.mark.asyncio
async def test_save_skill_workspace_forbidden_for_non_member(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """Non-member (no row returned) raises ForbiddenError."""
    no_member_result = MagicMock()
    no_member_result.scalar.return_value = None
    mock_session.execute = AsyncMock(return_value=no_member_result)

    with pytest.raises(ForbiddenError, match="Not a member of this workspace"):
        await service.save_skill(_workspace_save_payload())


@pytest.mark.asyncio
async def test_save_skill_personal_no_role_check(
    service: SkillGeneratorService,
    mock_session: AsyncMock,
) -> None:
    """Personal saves do NOT trigger role query — execute not called for role check."""
    payload = SkillSavePayload(
        workspace_id=_WORKSPACE_ID,
        user_id=_USER_ID,
        session_id=_SESSION_ID,
        save_type="personal",
        name="Personal Skill",
        description="desc",
        category="general",
        icon="Wand2",
        skill_content="# Personal\n\nContent.",
        example_prompts=["test"],
        graph_data=None,
    )

    result = await service.save_skill(payload)

    assert result.save_type == "personal"
    # session.execute should NOT have been called (no role query for personal saves)
    mock_session.execute.assert_not_awaited()
