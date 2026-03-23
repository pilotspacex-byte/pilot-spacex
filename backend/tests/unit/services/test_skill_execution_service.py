"""Unit tests for SkillExecutionService and SkillDefinitionParser.

Coverage:
- SkillDefinitionParser: valid frontmatter, missing fields, invalid approval mode,
  invalid required_approval_role, missing file, bad YAML.
- SkillExecutionService: approval modes (auto/suggest/require), TipTap validation,
  concurrency slot acquisition/release, C-7 required_approval_role enforcement,
  workspace mismatch guard, intent not found guard.

Feature 015: AI Workforce Platform (T-044, T-045)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from pilot_space.application.services.skill.skill_definition import (
    ApprovalMode,
    RequiredApprovalRole,
    SkillDefinition,
    SkillDefinitionError,
    SkillDefinitionParser,
)
from pilot_space.application.services.skill.skill_execution_service import (
    ExecuteSkillPayload,
    SkillExecutionService,
    SkillOutputValidationError,
)
from pilot_space.domain.exceptions import ForbiddenError, NotFoundError
from pilot_space.domain.work_intent import WorkIntent
from pilot_space.infrastructure.database.models.skill_execution import (
    SkillApprovalRole,
    SkillApprovalStatus,
    SkillExecution,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTO_FRONTMATTER = """\
---
name: review-code
description: Review code in note
approval: auto
model: opus
tools: [write_to_note, insert_block]
---
"""

_SUGGEST_FRONTMATTER = """\
---
name: generate-code
description: Generate code
approval: suggest
model: sonnet
tools: [write_to_note, insert_block, replace_content]
required_approval_role: member
---
"""

_REQUIRE_FRONTMATTER = """\
---
name: generate-migration
description: Generate migration
approval: require
model: sonnet
tools: [write_to_note, insert_block, ask_user]
required_approval_role: admin
---
"""

_MISSING_NAME_FRONTMATTER = """\
---
description: No name here
approval: auto
model: sonnet
---
"""

_BAD_APPROVAL_FRONTMATTER = """\
---
name: bad-skill
description: Bad approval
approval: invalid_mode
model: sonnet
---
"""

_BAD_ROLE_FRONTMATTER = """\
---
name: bad-role
description: Bad role
approval: require
model: sonnet
required_approval_role: superadmin
---
"""

_NO_FRONTMATTER = "# Skill without frontmatter\n\nSome content here."


def _make_intent(workspace_id: UUID, intent_id: UUID | None = None) -> WorkIntent:
    return WorkIntent(
        id=intent_id or uuid4(),
        workspace_id=workspace_id,
        what="Implement feature X",
        why="Needed for sprint",
        constraints=[],
        acceptance=[],
        confidence=0.9,
    )


def _valid_tiptap_doc() -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Generated code here"}],
            }
        ],
    }


# ---------------------------------------------------------------------------
# SkillDefinitionParser tests
# ---------------------------------------------------------------------------


class TestSkillDefinitionParser:
    def _parser_with_mock_file(
        self, skill_name: str, content: str, tmp_path: Path
    ) -> SkillDefinitionParser:
        """Create a parser pointing to a temp directory with the skill file."""
        skill_dir = tmp_path / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return SkillDefinitionParser(skills_base_path=tmp_path)

    @pytest.mark.asyncio
    async def test_parse_auto_approval(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("review-code", _AUTO_FRONTMATTER, tmp_path)
        defn = await parser.parse("review-code")

        assert defn.name == "review-code"
        assert defn.approval == ApprovalMode.AUTO
        assert defn.model == "opus"
        assert "write_to_note" in defn.tools
        assert defn.required_approval_role is None

    @pytest.mark.asyncio
    async def test_parse_suggest_with_member_role(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("generate-code", _SUGGEST_FRONTMATTER, tmp_path)
        defn = await parser.parse("generate-code")

        assert defn.approval == ApprovalMode.SUGGEST
        assert defn.required_approval_role == RequiredApprovalRole.MEMBER

    @pytest.mark.asyncio
    async def test_parse_require_with_admin_role(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("generate-migration", _REQUIRE_FRONTMATTER, tmp_path)
        defn = await parser.parse("generate-migration")

        assert defn.approval == ApprovalMode.REQUIRE
        assert defn.required_approval_role == RequiredApprovalRole.ADMIN

    @pytest.mark.asyncio
    async def test_parse_missing_required_field_raises(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("bad-skill", _MISSING_NAME_FRONTMATTER, tmp_path)
        with pytest.raises(SkillDefinitionError, match="missing required fields"):
            await parser.parse("bad-skill")

    @pytest.mark.asyncio
    async def test_parse_invalid_approval_mode_raises(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("bad-skill", _BAD_APPROVAL_FRONTMATTER, tmp_path)
        with pytest.raises(SkillDefinitionError, match="Invalid approval mode"):
            await parser.parse("bad-skill")

    @pytest.mark.asyncio
    async def test_parse_invalid_required_role_raises(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("bad-role", _BAD_ROLE_FRONTMATTER, tmp_path)
        with pytest.raises(SkillDefinitionError, match="Invalid required_approval_role"):
            await parser.parse("bad-role")

    @pytest.mark.asyncio
    async def test_parse_no_frontmatter_raises(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("no-fm", _NO_FRONTMATTER, tmp_path)
        with pytest.raises(SkillDefinitionError, match="No YAML frontmatter"):
            await parser.parse("no-fm")

    @pytest.mark.asyncio
    async def test_parse_missing_file_raises(self, tmp_path: Path) -> None:
        parser = SkillDefinitionParser(skills_base_path=tmp_path)
        with pytest.raises(SkillDefinitionError, match="not found"):
            await parser.parse("non-existent-skill")

    @pytest.mark.asyncio
    async def test_parse_tools_list(self, tmp_path: Path) -> None:
        parser = self._parser_with_mock_file("review-code", _AUTO_FRONTMATTER, tmp_path)
        defn = await parser.parse("review-code")
        assert isinstance(defn.tools, list)
        assert len(defn.tools) == 2

    @pytest.mark.asyncio
    async def test_parse_tools_empty_when_omitted(self, tmp_path: Path) -> None:
        content = (
            "---\nname: minimal\ndescription: Minimal skill\napproval: auto\nmodel: sonnet\n---\n"
        )
        parser = self._parser_with_mock_file("minimal", content, tmp_path)
        defn = await parser.parse("minimal")
        assert defn.tools == []


# ---------------------------------------------------------------------------
# Fixtures for SkillExecutionService
# ---------------------------------------------------------------------------


def _make_execution(
    intent_id: UUID,
    skill_name: str,
    approval_status: SkillApprovalStatus,
    required_role: SkillApprovalRole | None = None,
) -> SkillExecution:
    """Build a minimal SkillExecution ORM mock."""
    execution = MagicMock(spec=SkillExecution)
    execution.id = uuid4()
    execution.intent_id = intent_id
    execution.skill_name = skill_name
    execution.approval_status = approval_status
    execution.required_approval_role = required_role
    execution.output = _valid_tiptap_doc()
    return execution


def _make_service(
    *,
    session: Any | None = None,
    skill_exec_repo: Any | None = None,
    intent_repo: Any | None = None,
    concurrency_manager: Any | None = None,
    definition_parser: Any | None = None,
) -> SkillExecutionService:
    return SkillExecutionService(
        session=session or AsyncMock(),
        skill_exec_repo=skill_exec_repo or AsyncMock(),
        intent_repo=intent_repo or AsyncMock(),
        concurrency_manager=concurrency_manager or AsyncMock(),
        definition_parser=definition_parser,
    )


def _make_mock_parser(
    approval: ApprovalMode,
    required_role: RequiredApprovalRole | None,
    skill_name: str = "test-skill",
) -> MagicMock:
    parser = MagicMock(spec=SkillDefinitionParser)
    parser.parse.return_value = SkillDefinition(
        name=skill_name,
        description="Test skill",
        model="sonnet",
        tools=["write_to_note"],
        approval=approval,
        required_approval_role=required_role,
    )
    return parser


# ---------------------------------------------------------------------------
# SkillExecutionService tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSkillExecutionServiceApprovalModes:
    async def test_auto_approval_sets_auto_approved_status(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        expected_execution = _make_execution(
            intent.id,  # type: ignore[arg-type]
            "review-code",
            SkillApprovalStatus.AUTO_APPROVED,
        )
        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.return_value = expected_execution

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(ApprovalMode.AUTO, None, "review-code")
        session = AsyncMock()

        service = _make_service(
            session=session,
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        result = await service.execute(payload)

        assert result.approval_status == SkillApprovalStatus.AUTO_APPROVED
        skill_exec_repo.create.assert_called_once()
        concurrency.acquire_slot.assert_called_once_with(workspace_id)
        concurrency.release_slot.assert_called_once_with(workspace_id)

    async def test_suggest_approval_sets_pending_approval_status(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        expected_execution = _make_execution(
            intent.id,  # type: ignore[arg-type]
            "generate-code",
            SkillApprovalStatus.PENDING_APPROVAL,
            SkillApprovalRole.MEMBER,
        )
        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.return_value = expected_execution

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(
            ApprovalMode.SUGGEST, RequiredApprovalRole.MEMBER, "generate-code"
        )

        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="generate-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        result = await service.execute(payload)

        assert result.approval_status == SkillApprovalStatus.PENDING_APPROVAL

    async def test_require_approval_sets_pending_approval_status(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        expected_execution = _make_execution(
            intent.id,  # type: ignore[arg-type]
            "generate-migration",
            SkillApprovalStatus.PENDING_APPROVAL,
            SkillApprovalRole.ADMIN,
        )
        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.return_value = expected_execution

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(
            ApprovalMode.REQUIRE, RequiredApprovalRole.ADMIN, "generate-migration"
        )

        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="generate-migration",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        result = await service.execute(payload)

        assert result.approval_status == SkillApprovalStatus.PENDING_APPROVAL
        # Verify required_approval_role is ADMIN (C-7)
        assert result.required_approval_role == SkillApprovalRole.ADMIN


@pytest.mark.asyncio
class TestSkillExecutionServiceGuards:
    async def test_intent_not_found_raises_value_error(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = None

        parser = _make_mock_parser(ApprovalMode.AUTO, None)
        service = _make_service(intent_repo=intent_repo, definition_parser=parser)

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        with pytest.raises(NotFoundError, match="not found"):
            await service.execute(payload)

    async def test_workspace_mismatch_raises_value_error(self) -> None:
        workspace_id = uuid4()
        other_workspace = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = other_workspace  # Different workspace

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        parser = _make_mock_parser(ApprovalMode.AUTO, None)
        service = _make_service(intent_repo=intent_repo, definition_parser=parser)

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        with pytest.raises(ForbiddenError, match="workspace"):
            await service.execute(payload)

    async def test_concurrency_limit_raises_runtime_error(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = False  # Limit reached

        parser = _make_mock_parser(ApprovalMode.AUTO, None)
        service = _make_service(
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        with pytest.raises(RuntimeError, match="concurrent skill execution limit"):
            await service.execute(payload)

    async def test_slot_released_on_persist_error(self) -> None:
        """Ensure concurrency slot is released even if persist fails."""
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.side_effect = RuntimeError("DB error")

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(ApprovalMode.AUTO, None)
        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        with pytest.raises(RuntimeError, match="DB error"):
            await service.execute(payload)

        # Slot must be released despite error
        concurrency.release_slot.assert_called_once_with(workspace_id)


@pytest.mark.asyncio
class TestTipTapValidation:
    def _svc(self) -> SkillExecutionService:
        return _make_service()

    async def test_valid_doc_passes(self) -> None:
        svc = self._svc()
        # Should not raise
        svc._validate_tiptap_output(_valid_tiptap_doc(), "test-skill")

    async def test_non_dict_raises(self) -> None:
        svc = self._svc()
        with pytest.raises(SkillOutputValidationError, match="must be a JSON object"):
            svc._validate_tiptap_output("invalid", "test-skill")  # type: ignore[arg-type]

    async def test_missing_type_raises(self) -> None:
        svc = self._svc()
        with pytest.raises(SkillOutputValidationError, match="'type' field"):
            svc._validate_tiptap_output({"content": []}, "test-skill")

    async def test_invalid_content_type_raises(self) -> None:
        svc = self._svc()
        bad_doc = {"type": "doc", "content": "not a list"}
        with pytest.raises(SkillOutputValidationError, match="invalid 'content'"):
            svc._validate_tiptap_output(bad_doc, "test-skill")

    async def test_non_dict_child_raises(self) -> None:
        svc = self._svc()
        bad_doc = {"type": "doc", "content": ["not a dict"]}
        with pytest.raises(SkillOutputValidationError, match="must be a JSON object"):
            svc._validate_tiptap_output(bad_doc, "test-skill")

    async def test_nested_invalid_node_raises(self) -> None:
        svc = self._svc()
        bad_doc = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"no_type": True}]},
            ],
        }
        with pytest.raises(SkillOutputValidationError, match="missing/invalid 'type'"):
            svc._validate_tiptap_output(bad_doc, "test-skill")

    async def test_leaf_node_without_content_passes(self) -> None:
        svc = self._svc()
        doc = {
            "type": "doc",
            "content": [{"type": "text", "text": "Hello"}],
        }
        # Leaf types (text) do not require content — should not raise
        svc._validate_tiptap_output(doc, "test-skill")

    async def test_code_block_without_content_passes(self) -> None:
        svc = self._svc()
        doc = {
            "type": "doc",
            "content": [{"type": "codeBlock", "attrs": {"language": "python"}}],
        }
        # codeBlock with no content array is valid (empty block)
        svc._validate_tiptap_output(doc, "test-skill")


# ---------------------------------------------------------------------------
# C-7: Required approval role enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRequiredApprovalRoleC7:
    async def test_member_role_on_suggest_persisted_correctly(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        execution_slot: list[SkillExecution] = []

        async def capture_create(execution: SkillExecution) -> SkillExecution:
            execution_slot.append(execution)
            return execution

        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.side_effect = capture_create

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(ApprovalMode.SUGGEST, RequiredApprovalRole.MEMBER, "write-tests")
        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="write-tests",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        await service.execute(payload)

        assert len(execution_slot) == 1
        persisted = execution_slot[0]
        assert persisted.required_approval_role == SkillApprovalRole.MEMBER
        assert persisted.approval_status == SkillApprovalStatus.PENDING_APPROVAL

    async def test_admin_role_on_require_persisted_correctly(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        execution_slot: list[SkillExecution] = []

        async def capture_create(execution: SkillExecution) -> SkillExecution:
            execution_slot.append(execution)
            return execution

        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.side_effect = capture_create

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(
            ApprovalMode.REQUIRE, RequiredApprovalRole.ADMIN, "generate-migration"
        )
        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="generate-migration",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        await service.execute(payload)

        assert len(execution_slot) == 1
        persisted = execution_slot[0]
        assert persisted.required_approval_role == SkillApprovalRole.ADMIN
        assert persisted.approval_status == SkillApprovalStatus.PENDING_APPROVAL

    async def test_no_role_on_auto_persisted_correctly(self) -> None:
        workspace_id = uuid4()
        intent = _make_intent(workspace_id)

        intent_model = MagicMock()
        intent_model.workspace_id = workspace_id

        intent_repo = AsyncMock()
        intent_repo.get_by_id.return_value = intent_model

        execution_slot: list[SkillExecution] = []

        async def capture_create(execution: SkillExecution) -> SkillExecution:
            execution_slot.append(execution)
            return execution

        skill_exec_repo = AsyncMock()
        skill_exec_repo.create.side_effect = capture_create

        concurrency = AsyncMock()
        concurrency.acquire_slot.return_value = True

        parser = _make_mock_parser(ApprovalMode.AUTO, None, "review-code")
        service = _make_service(
            skill_exec_repo=skill_exec_repo,
            intent_repo=intent_repo,
            concurrency_manager=concurrency,
            definition_parser=parser,
        )

        payload = ExecuteSkillPayload(
            intent=intent,
            skill_name="review-code",
            output=_valid_tiptap_doc(),
            workspace_id=workspace_id,
            user_id=uuid4(),
        )
        await service.execute(payload)

        persisted = execution_slot[0]
        assert persisted.required_approval_role is None
        assert persisted.approval_status == SkillApprovalStatus.AUTO_APPROVED
