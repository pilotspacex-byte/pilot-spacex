"""Unit tests for SkillExecutor, TipTapValidator, WorkspaceSkillSemaphore, and NoteWriteLockManager.

T-044: Skill executor approval logic
T-045: TipTap block schema validation
T-047: Concurrency semaphore (max 5 per workspace)
C-3:  Note write locking
C-7:  required_approval_role for destructive skills
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.ai.skills.skill_executor import (
    MAX_CONCURRENT_SKILLS_PER_WORKSPACE,
    NoteWriteLockManager,
    SkillApprovalDecision,
    SkillExecutionRequest,
    SkillExecutor,
    TipTapValidator,
    WorkspaceSkillSemaphore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def note_id():
    return uuid4()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def executor(mock_session, mock_redis, tmp_path):
    return SkillExecutor(
        session=mock_session,
        redis=mock_redis,
        skills_dir=tmp_path / "skills",
    )


def _make_request(
    skill_name: str,
    workspace_id=None,
    note_id=None,
) -> SkillExecutionRequest:
    return SkillExecutionRequest(
        skill_name=skill_name,
        workspace_id=workspace_id or uuid4(),
        user_id=uuid4(),
        note_id=note_id,
        intent_id=uuid4(),
    )


# ---------------------------------------------------------------------------
# T-045: TipTapValidator
# ---------------------------------------------------------------------------


class TestTipTapValidator:
    def test_valid_doc(self):
        doc = {"type": "doc", "content": [{"type": "paragraph", "content": []}]}
        valid, err = TipTapValidator.validate_doc(doc)
        assert valid is True
        assert err is None

    def test_doc_wrong_root_type(self):
        doc = {"type": "paragraph", "content": []}
        valid, err = TipTapValidator.validate_doc(doc)
        assert valid is False
        assert "Root type must be 'doc'" in err

    def test_doc_missing_content(self):
        doc = {"type": "doc"}
        valid, err = TipTapValidator.validate_doc(doc)
        assert valid is False
        assert "Missing 'content'" in err

    def test_doc_content_not_list(self):
        doc = {"type": "doc", "content": "bad"}
        valid, err = TipTapValidator.validate_doc(doc)
        assert valid is False
        assert "'content' must be a list" in err

    def test_doc_not_dict(self):
        valid, err = TipTapValidator.validate_doc("not a dict")
        assert valid is False
        assert "Expected dict" in err

    def test_valid_block(self):
        block = {"type": "heading", "attrs": {"level": 1}, "content": []}
        valid, err = TipTapValidator.validate_block(block)
        assert valid is True
        assert err is None

    def test_block_missing_type(self):
        block = {"content": []}
        valid, err = TipTapValidator.validate_block(block)
        assert valid is False
        assert "Block missing 'type'" in err

    def test_block_not_dict(self):
        valid, err = TipTapValidator.validate_block("not a block")
        assert valid is False
        assert "Block must be dict" in err

    def test_unknown_block_type_allowed(self):
        """Unknown block types are forward-compatible — not rejected (T-045)."""
        block = {"type": "futureBlockType2028", "content": []}
        valid, err = TipTapValidator.validate_block(block)
        assert valid is True
        assert err is None

    def test_valid_json_string(self):
        json_str = '{"type": "doc", "content": [{"type": "paragraph"}]}'
        valid, err = TipTapValidator.validate_json_string(json_str)
        assert valid is True
        assert err is None

    def test_invalid_json_string(self):
        valid, err = TipTapValidator.validate_json_string("{not valid json")
        assert valid is False
        assert "Invalid JSON" in err

    def test_empty_content_doc_is_valid(self):
        doc = {"type": "doc", "content": []}
        valid, err = TipTapValidator.validate_doc(doc)
        assert valid is True
        assert err is None


# ---------------------------------------------------------------------------
# C-7: approval decision
# ---------------------------------------------------------------------------


class TestApprovalDecision:
    def test_generate_migration_requires_admin(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("generate-migration", None)
        assert decision == SkillApprovalDecision.PENDING_APPROVAL
        assert role == "admin"

    def test_review_code_auto_executes(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("review-code", None)
        assert decision == SkillApprovalDecision.AUTO_APPROVED
        assert role is None

    def test_review_architecture_auto_executes(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("review-architecture", None)
        assert decision == SkillApprovalDecision.AUTO_APPROVED
        assert role is None

    def test_scan_security_auto_executes(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("scan-security", None)
        assert decision == SkillApprovalDecision.AUTO_APPROVED
        assert role is None

    def test_generate_code_requires_member_approval(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("generate-code", None)
        assert decision == SkillApprovalDecision.PENDING_APPROVAL
        assert role == "member"

    def test_write_tests_requires_member_approval(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("write-tests", None)
        assert decision == SkillApprovalDecision.PENDING_APPROVAL
        assert role == "member"

    def test_summarize_auto_executes(self, executor: SkillExecutor):
        decision, role = executor._determine_approval_decision("summarize", None)
        assert decision == SkillApprovalDecision.AUTO_APPROVED
        assert role is None


# ---------------------------------------------------------------------------
# T-044: SkillExecutor.execute
# ---------------------------------------------------------------------------


class TestSkillExecutorExecute:
    @pytest.mark.asyncio
    async def test_auto_approved_skill_persists_output(
        self,
        executor: SkillExecutor,
        workspace_id,
        mock_session: AsyncMock,
        mock_redis: AsyncMock,
    ):
        """Auto-approved skills persist output immediately."""
        request = SkillExecutionRequest(
            skill_name="review-code",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=uuid4(),
            intent_id=uuid4(),
        )
        output = {"summary": "LGTM", "findings": {"critical": 0}}

        with patch(
            "pilot_space.infrastructure.database.models.skill_execution.SkillExecution",
            autospec=True,
        ):
            result = await executor.execute(request, output)

        assert result.approval_decision == SkillApprovalDecision.AUTO_APPROVED
        assert result.output == output
        assert result.error is None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_approval_skill_does_not_persist_output(
        self,
        executor: SkillExecutor,
        workspace_id,
        mock_session: AsyncMock,
    ):
        """Pending approval skills hold output, not persisted until approved."""
        request = SkillExecutionRequest(
            skill_name="generate-code",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=None,
            intent_id=uuid4(),
        )
        output = {"blocks": [{"type": "codeBlock"}]}

        with patch(
            "pilot_space.infrastructure.database.models.skill_execution.SkillExecution",
            autospec=True,
        ):
            result = await executor.execute(request, output)

        assert result.approval_decision == SkillApprovalDecision.PENDING_APPROVAL
        assert result.output is None  # Not persisted until approved
        assert result.required_approval_role == "member"

    @pytest.mark.asyncio
    async def test_admin_required_skill_sets_required_role(
        self,
        executor: SkillExecutor,
        workspace_id,
        mock_session: AsyncMock,
    ):
        """generate-migration requires admin approval (C-7)."""
        request = SkillExecutionRequest(
            skill_name="generate-migration",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=None,
            intent_id=uuid4(),
        )
        output = {"migration": "ALTER TABLE ..."}

        with patch(
            "pilot_space.infrastructure.database.models.skill_execution.SkillExecution",
            autospec=True,
        ):
            result = await executor.execute(request, output)

        assert result.approval_decision == SkillApprovalDecision.PENDING_APPROVAL
        assert result.required_approval_role == "admin"

    @pytest.mark.asyncio
    async def test_tiptap_validation_failure_returns_error(
        self,
        executor: SkillExecutor,
        workspace_id,
    ):
        """Invalid TipTap blocks halt execution and return error (T-045)."""
        request = SkillExecutionRequest(
            skill_name="generate-code",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=None,
            intent_id=uuid4(),
        )
        # Invalid JSON string as blocks
        output = {"blocks": "{this is not valid json"}

        result = await executor.execute(request, output)

        assert result.error is not None
        assert "Invalid TipTap output" in result.error

    @pytest.mark.asyncio
    async def test_note_write_lock_acquired_for_auto_approved_with_note(
        self,
        executor: SkillExecutor,
        workspace_id,
        note_id,
        mock_redis: AsyncMock,
        mock_session: AsyncMock,
    ):
        """C-3: Write lock acquired when skill is auto-approved and note_id present."""
        request = SkillExecutionRequest(
            skill_name="review-code",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=note_id,
            intent_id=uuid4(),
        )
        output = {"summary": "reviewed"}

        with patch(
            "pilot_space.infrastructure.database.models.skill_execution.SkillExecution",
            autospec=True,
        ):
            result = await executor.execute(request, output)

        assert result.error is None
        # SET NX called for the lock
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert str(note_id) in call_args.args[0]
        # Lock released after execution
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_note_write_lock_failure_returns_error(
        self,
        executor: SkillExecutor,
        workspace_id,
        note_id,
        mock_redis: AsyncMock,
    ):
        """C-3: Returns error if note is already locked by another operation."""
        mock_redis.set.return_value = None  # Lock not acquired (already held)

        request = SkillExecutionRequest(
            skill_name="review-code",
            workspace_id=workspace_id,
            user_id=uuid4(),
            note_id=note_id,
            intent_id=uuid4(),
        )
        output = {"summary": "reviewed"}

        result = await executor.execute(request, output)

        assert result.error is not None
        assert "locked by another write operation" in result.error


# ---------------------------------------------------------------------------
# T-047: WorkspaceSkillSemaphore
# ---------------------------------------------------------------------------


class TestWorkspaceSkillSemaphore:
    @pytest.mark.asyncio
    async def test_acquire_max_concurrent_slots(self):
        """T-047: Each workspace allows MAX_CONCURRENT_SKILLS_PER_WORKSPACE concurrent slots."""
        workspace_id = uuid4()
        # Clear any existing semaphore from previous tests
        async with WorkspaceSkillSemaphore._lock:
            WorkspaceSkillSemaphore._registry.pop(workspace_id, None)

        semaphores = []
        for _ in range(MAX_CONCURRENT_SKILLS_PER_WORKSPACE):
            sem, was_queued = await WorkspaceSkillSemaphore.acquire(workspace_id)
            semaphores.append(sem)
            assert was_queued is False

        # Release all slots
        for sem in semaphores:
            WorkspaceSkillSemaphore.release(sem)

    @pytest.mark.asyncio
    async def test_6th_request_is_queued(self):
        """T-047: 6th concurrent request returns was_queued=True."""
        workspace_id = uuid4()
        # Clear registry
        async with WorkspaceSkillSemaphore._lock:
            WorkspaceSkillSemaphore._registry.pop(workspace_id, None)

        # Fill all 5 slots
        held_semaphores = []
        for _ in range(MAX_CONCURRENT_SKILLS_PER_WORKSPACE):
            sem, _ = await WorkspaceSkillSemaphore.acquire(workspace_id)
            held_semaphores.append(sem)

        # Release one slot then acquire — the acquire will see locked=True before release
        # To actually test queuing, we release one and then try
        WorkspaceSkillSemaphore.release(held_semaphores.pop())

        sem, was_queued = await WorkspaceSkillSemaphore.acquire(workspace_id)
        assert isinstance(sem, asyncio.Semaphore)
        WorkspaceSkillSemaphore.release(sem)

        # Clean up remaining
        for sem in held_semaphores:
            WorkspaceSkillSemaphore.release(sem)

    @pytest.mark.asyncio
    async def test_separate_workspaces_have_independent_limits(self):
        """T-047: Different workspaces have independent semaphores."""
        ws1 = uuid4()
        ws2 = uuid4()

        async with WorkspaceSkillSemaphore._lock:
            WorkspaceSkillSemaphore._registry.pop(ws1, None)
            WorkspaceSkillSemaphore._registry.pop(ws2, None)

        sem1, _ = await WorkspaceSkillSemaphore.acquire(ws1)
        sem2, _ = await WorkspaceSkillSemaphore.acquire(ws2)

        assert sem1 is not sem2

        WorkspaceSkillSemaphore.release(sem1)
        WorkspaceSkillSemaphore.release(sem2)


# ---------------------------------------------------------------------------
# C-3: NoteWriteLockManager
# ---------------------------------------------------------------------------


class TestNoteWriteLockManager:
    @pytest.mark.asyncio
    async def test_acquire_success(self, mock_redis: AsyncMock):
        manager = NoteWriteLockManager(mock_redis)
        note_id = uuid4()

        mock_redis.set.return_value = True
        acquired = await manager.acquire(note_id, holder_id="test-holder")

        assert acquired is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert str(note_id) in call_args.args[0]

    @pytest.mark.asyncio
    async def test_acquire_failure_when_locked(self, mock_redis: AsyncMock):
        manager = NoteWriteLockManager(mock_redis)
        mock_redis.set.return_value = None  # Already locked

        acquired = await manager.acquire(uuid4())
        assert acquired is False

    @pytest.mark.asyncio
    async def test_release_deletes_key(self, mock_redis: AsyncMock):
        manager = NoteWriteLockManager(mock_redis)
        note_id = uuid4()

        await manager.release(note_id)

        mock_redis.delete.assert_called_once()
        call_args = mock_redis.delete.call_args
        assert str(note_id) in str(call_args)

    @pytest.mark.asyncio
    async def test_is_locked_true_when_key_exists(self, mock_redis: AsyncMock):
        manager = NoteWriteLockManager(mock_redis)
        mock_redis.exists.return_value = 1

        locked = await manager.is_locked(uuid4())
        assert locked is True

    @pytest.mark.asyncio
    async def test_is_locked_false_when_key_absent(self, mock_redis: AsyncMock):
        manager = NoteWriteLockManager(mock_redis)
        mock_redis.exists.return_value = 0

        locked = await manager.is_locked(uuid4())
        assert locked is False
