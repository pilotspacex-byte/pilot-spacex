"""Unit tests for MemberProfileService.

Tests:
- get_profile: workspace not found
- get_profile: requester not a member
- get_profile: target member not found
- get_profile: no cycles, zero available hours → all stats zero
- get_profile: full stats with cycles, active cycle, PR links
- get_profile: capacity utilization clamped at 100%
- get_profile: no active cycle → committed hours 0
- get_profile: no PR links → count 0
- get_activity: workspace not found
- get_activity: requester not a member
- get_activity: pagination (page_size clamped to 50)
- get_activity: type_filter forwarded to query
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pilot_space.application.services.workspace_member import (
    GetMemberActivityPayload,
    GetMemberProfilePayload,
    MemberNotFoundError,
    MemberProfileService,
    UnauthorizedError,
    WorkspaceNotFoundError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _make_member(user_id: uuid.UUID, weekly_hours: float = 40.0) -> MagicMock:
    """Build a mock WorkspaceMember with required attributes."""
    member = MagicMock()
    member.user_id = user_id
    member.weekly_available_hours = weekly_hours
    role = MagicMock()
    role.value = "member"
    member.role = role
    member.created_at = datetime.now(UTC)
    user = MagicMock()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.avatar_url = None
    member.user = user
    return member


def _make_workspace(members: list) -> MagicMock:
    ws = MagicMock()
    ws.members = members
    return ws


def _make_service(
    session: MagicMock,
    workspace_repo: MagicMock,
) -> MemberProfileService:
    return MemberProfileService(session=session, workspace_repo=workspace_repo)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_repo() -> MagicMock:
    return AsyncMock()


@pytest.fixture
def mock_session() -> MagicMock:
    return AsyncMock()


# ---------------------------------------------------------------------------
# get_profile — error paths
# ---------------------------------------------------------------------------


class TestGetProfileErrors:
    """Error-path tests for MemberProfileService.get_profile."""

    @pytest.mark.asyncio
    async def test_workspace_not_found(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Raises WorkspaceNotFoundError when workspace does not exist."""
        workspace_repo.get_with_members.return_value = None
        svc = _make_service(mock_session, workspace_repo)

        with pytest.raises(WorkspaceNotFoundError, match="Workspace not found"):
            await svc.get_profile(
                GetMemberProfilePayload(
                    workspace_id=_make_uuid(),
                    user_id=_make_uuid(),
                    requesting_user_id=_make_uuid(),
                )
            )

    @pytest.mark.asyncio
    async def test_requester_not_member(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Raises UnauthorizedError when requesting user is not in the workspace."""
        workspace_repo.get_with_members.return_value = _make_workspace([])
        svc = _make_service(mock_session, workspace_repo)

        with pytest.raises(UnauthorizedError, match="Not a member"):
            await svc.get_profile(
                GetMemberProfilePayload(
                    workspace_id=_make_uuid(),
                    user_id=_make_uuid(),
                    requesting_user_id=_make_uuid(),
                )
            )

    @pytest.mark.asyncio
    async def test_target_member_not_found(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Raises MemberNotFoundError when user_id does not match any member."""
        requester_id = _make_uuid()
        requester = _make_member(requester_id)
        workspace_repo.get_with_members.return_value = _make_workspace([requester])
        svc = _make_service(mock_session, workspace_repo)

        with pytest.raises(MemberNotFoundError, match="Member not found"):
            await svc.get_profile(
                GetMemberProfilePayload(
                    workspace_id=_make_uuid(),
                    user_id=_make_uuid(),  # different from requester_id
                    requesting_user_id=requester_id,
                )
            )


# ---------------------------------------------------------------------------
# get_profile — stats computation
# ---------------------------------------------------------------------------


class TestGetProfileStats:
    """Stats-computation tests for MemberProfileService.get_profile."""

    def _build_execute_stub(self, call_map: dict[int, MagicMock]):
        """Return an async callable that returns a different mock per call index."""
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = call_map[call_count]
            call_count += 1
            return result

        return _execute

    def _scalar_result(self, value) -> MagicMock:
        r = MagicMock()
        r.scalar.return_value = value
        return r

    def _scalars_all_result(self, values: list) -> MagicMock:
        r = MagicMock()
        r.scalars.return_value.all.return_value = values
        return r

    @pytest.mark.asyncio
    async def test_no_cycles_zero_available_hours(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """All stats are 0 when there are no cycles and weekly_hours=0."""
        user_id = _make_uuid()
        member = _make_member(user_id, weekly_hours=0.0)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1 (gather, parallel):
        # 0 → issues_created (scalar=0)
        # 1 → issues_assigned (scalar=0)
        # 2 → cycle_ids (scalars=[])      → no closed-count query in group 2
        # 3 → active_cycle_id (scalar=None) → no committed query in group 2
        # 4 → pr_count (scalar=0)
        call_map = {
            0: self._scalar_result(0),
            1: self._scalar_result(0),
            2: self._scalars_all_result([]),
            3: self._scalar_result(None),
            4: self._scalar_result(0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.issues_created == 0
        assert result.issues_assigned == 0
        assert result.cycle_velocity == 0.0
        assert result.capacity_utilization_pct == 0.0
        assert result.pr_commit_links_count == 0

    @pytest.mark.asyncio
    async def test_all_stats_computed_correctly(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """All five stats computed correctly with realistic data.

        cycle_velocity = 4 closed / 2 cycles = 2.0
        capacity_utilization_pct = (20 / 40) * 100 = 50.0
        """
        user_id = _make_uuid()
        cycle_id_1 = _make_uuid()
        cycle_id_2 = _make_uuid()
        member = _make_member(user_id, weekly_hours=40.0)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1 (gather, parallel):
        # 0 → issues_created=5
        # 1 → issues_assigned=8
        # 2 → last-3 cycle IDs=[cycle_id_1, cycle_id_2]
        # 3 → active_cycle_id=cycle_id_1
        # 4 → pr_count=3
        # Group 2 (gather, parallel, depends on group 1):
        # 5 → total_closed=4  (4/2 = 2.0 velocity)
        # 6 → committed_hours=20.0  (20/40 = 50%)
        call_map = {
            0: self._scalar_result(5),
            1: self._scalar_result(8),
            2: self._scalars_all_result([cycle_id_1, cycle_id_2]),
            3: self._scalar_result(cycle_id_1),
            4: self._scalar_result(3),
            5: self._scalar_result(4),
            6: self._scalar_result(20.0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.issues_created == 5
        assert result.issues_assigned == 8
        assert result.cycle_velocity == pytest.approx(2.0)
        assert result.capacity_utilization_pct == pytest.approx(50.0)
        assert result.pr_commit_links_count == 3
        assert result.member is member

    @pytest.mark.asyncio
    async def test_capacity_utilization_clamped_at_100(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """capacity_utilization_pct must not exceed 100 when over-allocated."""
        user_id = _make_uuid()
        active_cycle_id = _make_uuid()
        member = _make_member(user_id, weekly_hours=40.0)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1 (gather, parallel):
        # 0 → issues_created=0, 1 → issues_assigned=0
        # 2 → cycle_ids=[]  (no closed-count query in group 2)
        # 3 → active_cycle_id=active_cycle_id
        # 4 → pr_count=0
        # Group 2:
        # 5 → committed_hours=80.0  (80/40*100=200% → clamped to 100)
        call_map = {
            0: self._scalar_result(0),
            1: self._scalar_result(0),
            2: self._scalars_all_result([]),
            3: self._scalar_result(active_cycle_id),
            4: self._scalar_result(0),
            5: self._scalar_result(80.0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.capacity_utilization_pct == 100.0

    @pytest.mark.asyncio
    async def test_no_active_cycle_committed_hours_zero(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """committed_hours=0 and utilization=0 when no active cycle."""
        user_id = _make_uuid()
        member = _make_member(user_id, weekly_hours=40.0)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1 (gather, parallel):
        # 0 → issues_created=2, 1 → issues_assigned=3
        # 2 → cycle_ids=[]  (no closed-count query)
        # 3 → active_cycle_id=None  (no committed query)
        # 4 → pr_count=1
        call_map = {
            0: self._scalar_result(2),
            1: self._scalar_result(3),
            2: self._scalars_all_result([]),
            3: self._scalar_result(None),
            4: self._scalar_result(1),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.capacity_utilization_pct == 0.0

    @pytest.mark.asyncio
    async def test_no_pr_links(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """pr_commit_links_count=0 when query returns 0."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1: issues_created=0, issues_assigned=0, cycle_ids=[], active=None, pr=0
        call_map = {
            0: self._scalar_result(0),
            1: self._scalar_result(0),
            2: self._scalars_all_result([]),
            3: self._scalar_result(None),
            4: self._scalar_result(0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.pr_commit_links_count == 0

    @pytest.mark.asyncio
    async def test_cycle_velocity_single_cycle(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """cycle_velocity = closed / 1 when only one completed cycle."""
        user_id = _make_uuid()
        cycle_id = _make_uuid()
        member = _make_member(user_id, weekly_hours=40.0)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1 (gather, parallel):
        # 0 → issues_created=0, 1 → issues_assigned=0
        # 2 → cycle_ids=[cycle_id]
        # 3 → active_cycle_id=None  (no committed query)
        # 4 → pr_count=0
        # Group 2:
        # 5 → total_closed=3  (3/1 = 3.0 velocity)
        call_map = {
            0: self._scalar_result(0),
            1: self._scalar_result(0),
            2: self._scalars_all_result([cycle_id]),
            3: self._scalar_result(None),
            4: self._scalar_result(0),
            5: self._scalar_result(3),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.cycle_velocity == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_requester_and_target_can_be_same_user(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """A member can request their own profile (self-view)."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        # Group 1: issues_created=0, issues_assigned=0, cycle_ids=[], active=None, pr=0
        call_map = {
            0: self._scalar_result(0),
            1: self._scalar_result(0),
            2: self._scalars_all_result([]),
            3: self._scalar_result(None),
            4: self._scalar_result(0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,  # same as user_id
            )
        )

        assert result.member is member

    @pytest.mark.asyncio
    async def test_different_requester_views_target_profile(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """A workspace member can view another member's profile."""
        requester_id = _make_uuid()
        target_id = _make_uuid()
        requester = _make_member(requester_id)
        target = _make_member(target_id, weekly_hours=20.0)
        workspace_repo.get_with_members.return_value = _make_workspace([requester, target])

        # Group 1: issues_created=1, issues_assigned=2, cycle_ids=[], active=None, pr=0
        call_map = {
            0: self._scalar_result(1),
            1: self._scalar_result(2),
            2: self._scalars_all_result([]),
            3: self._scalar_result(None),
            4: self._scalar_result(0),
        }
        mock_session.execute = self._build_execute_stub(call_map)

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_profile(
            GetMemberProfilePayload(
                workspace_id=_make_uuid(),
                user_id=target_id,
                requesting_user_id=requester_id,
            )
        )

        assert result.member is target
        assert result.issues_created == 1
        assert result.issues_assigned == 2


# ---------------------------------------------------------------------------
# get_activity — tests
# ---------------------------------------------------------------------------


class TestGetActivity:
    """Tests for MemberProfileService.get_activity."""

    def _build_activity_execute_stub(
        self,
        total: int,
        items: list,
    ):
        """Return an async callable: first call returns total count, second returns items."""
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar.return_value = total
            else:
                result.unique.return_value.scalars.return_value.all.return_value = items
            call_count += 1
            return result

        return _execute

    @pytest.mark.asyncio
    async def test_workspace_not_found(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Raises WorkspaceNotFoundError when workspace does not exist."""
        workspace_repo.get_with_members.return_value = None
        svc = _make_service(mock_session, workspace_repo)

        with pytest.raises(WorkspaceNotFoundError, match="Workspace not found"):
            await svc.get_activity(
                GetMemberActivityPayload(
                    workspace_id=_make_uuid(),
                    user_id=_make_uuid(),
                    requesting_user_id=_make_uuid(),
                )
            )

    @pytest.mark.asyncio
    async def test_requester_not_member(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Raises UnauthorizedError when requesting user is not in the workspace."""
        workspace_repo.get_with_members.return_value = _make_workspace([])
        svc = _make_service(mock_session, workspace_repo)

        with pytest.raises(UnauthorizedError, match="Not a member"):
            await svc.get_activity(
                GetMemberActivityPayload(
                    workspace_id=_make_uuid(),
                    user_id=_make_uuid(),
                    requesting_user_id=_make_uuid(),
                )
            )

    @pytest.mark.asyncio
    async def test_page_size_clamped_to_50(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """page_size > 50 is silently clamped to 50."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        activity = MagicMock()
        activity.issue = None
        mock_session.execute = self._build_activity_execute_stub(
            total=100,
            items=[activity] * 20,
        )

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_activity(
            GetMemberActivityPayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
                page=1,
                page_size=200,
            )
        )

        assert result.page_size == 50
        assert result.page == 1
        assert result.total == 100
        assert len(result.items) == 20

    @pytest.mark.asyncio
    async def test_pagination_page_2(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """page is forwarded to result unchanged."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        mock_session.execute = self._build_activity_execute_stub(total=55, items=[])

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_activity(
            GetMemberActivityPayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
                page=2,
                page_size=20,
            )
        )

        assert result.page == 2
        assert result.total == 55
        assert result.page_size == 20

    @pytest.mark.asyncio
    async def test_type_filter_accepted(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """type_filter param is accepted without error (filter applied in query)."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        execute_calls: list[int] = []

        original_stub = self._build_activity_execute_stub(total=3, items=[])

        async def counting_stub(stmt):
            execute_calls.append(1)
            return await original_stub(stmt)

        mock_session.execute = counting_stub

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_activity(
            GetMemberActivityPayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
                type_filter="issue_created",
            )
        )

        assert result.total == 3
        # execute called twice: count query + items query
        assert len(execute_calls) == 2

    @pytest.mark.asyncio
    async def test_empty_activity_returns_zero_total(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Returns total=0 and empty items list when no activity exists."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        mock_session.execute = self._build_activity_execute_stub(total=0, items=[])

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_activity(
            GetMemberActivityPayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
            )
        )

        assert result.total == 0
        assert result.items == []
        assert result.page_size == 20  # default

    @pytest.mark.asyncio
    async def test_page_size_at_exact_limit_50(
        self,
        workspace_repo: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """page_size=50 is accepted unchanged (boundary value)."""
        user_id = _make_uuid()
        member = _make_member(user_id)
        workspace_repo.get_with_members.return_value = _make_workspace([member])

        mock_session.execute = self._build_activity_execute_stub(total=10, items=[])

        svc = _make_service(mock_session, workspace_repo)
        result = await svc.get_activity(
            GetMemberActivityPayload(
                workspace_id=_make_uuid(),
                user_id=user_id,
                requesting_user_id=user_id,
                page_size=50,
            )
        )

        assert result.page_size == 50
