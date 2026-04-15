"""Tests for RichContextAssembler service.

Tests verify:
- Enriched context with KG decisions, related PRs, sprint peers
- Graceful degradation when enrichment sources fail
- Budget manager enforcing 60% cap with priority truncation
- TTL cache returning cached results
- Deduplication of KG results by node_id
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from pilot_space.api.v1.schemas.implement_context import (
    ImplementContextResponse,
    IssueDetail,
    IssueStateDetail,
    KGDecision,
    ProjectContext,
    RelatedPR,
    RepositoryContext,
    SprintPeer,
    WorkspaceContext,
)
from pilot_space.application.services.issue.rich_context_assembler import (
    RichContextAssembler,
    RichContextPayload,
    RichContextResult,
    _CACHE_TTL_SECONDS,
    _CHAR_BUDGET,
    _TOKEN_BUDGET,
    estimate_tokens,
)
from pilot_space.application.services.memory.memory_recall_service import (
    MemoryItem,
    RecallResult,
)
from pilot_space.infrastructure.database.models import IssuePriority, StateGroup


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def make_issue_detail(
    *,
    cycle_id: UUID | None = None,
    title: str = "Add OAuth login",
    description: str | None = "Implement Google OAuth",
) -> IssueDetail:
    return IssueDetail(
        id=uuid4(),
        identifier="PS-1",
        title=title,
        description=description,
        description_html=None,
        acceptance_criteria=["User can log in with Google"],
        status="unstarted",
        priority=IssuePriority.MEDIUM,
        labels=[],
        state=IssueStateDetail(
            id=uuid4(),
            name="Todo",
            color="#999",
            group=StateGroup.UNSTARTED,
        ),
        project_id=uuid4(),
        assignee_id=None,
        cycle_id=cycle_id,
    )


def make_base_context(issue: IssueDetail | None = None) -> ImplementContextResponse:
    if issue is None:
        issue = make_issue_detail()
    return ImplementContextResponse(
        issue=issue,
        linked_notes=[],
        repository=RepositoryContext(
            clone_url="https://github.com/org/repo",
            default_branch="main",
            provider="github",
        ),
        workspace=WorkspaceContext(slug="workspace", name="Test Workspace"),
        project=ProjectContext(name="Test Project", tech_stack_summary="FastAPI, React"),
        suggested_branch="feat/ps-1-add-oauth-login",
    )


def make_assembler(
    *,
    base_context: ImplementContextResponse | None = None,
    recall_items: list[MemoryItem] | None = None,
    recall_raise: Exception | None = None,
    issue_links: list[Any] | None = None,
    pr_links: list[Any] | None = None,
    cycle_issues: list[Any] | None = None,
) -> RichContextAssembler:
    """Build a RichContextAssembler with mocked dependencies."""
    if base_context is None:
        base_context = make_base_context()

    # Mock base_service
    base_service = MagicMock()
    from pilot_space.application.services.issue.get_implement_context_service import (
        GetImplementContextResult,
    )

    base_service.execute = AsyncMock(return_value=GetImplementContextResult(context=base_context))

    # Mock memory_recall
    memory_recall = MagicMock()
    if recall_raise:
        memory_recall.recall = AsyncMock(side_effect=recall_raise)
    else:
        items = recall_items or []
        memory_recall.recall = AsyncMock(
            return_value=RecallResult(items=items, cache_hit=False, elapsed_ms=0)
        )

    # Mock issue_link_repo
    issue_link_repo = MagicMock()
    issue_link_repo.find_all_for_issue = AsyncMock(return_value=issue_links or [])

    # Mock integration_link_repo
    integration_link_repo = MagicMock()
    integration_link_repo.get_pull_requests_for_issues = AsyncMock(return_value=pr_links or [])

    # Mock cycle_repo
    cycle_repo = MagicMock()
    cycle_repo.get_issues_in_cycle = AsyncMock(return_value=cycle_issues or [])

    # Always clear the class-level cache to avoid test pollution
    RichContextAssembler._cache.clear()

    return RichContextAssembler(
        base_service=base_service,
        memory_recall=memory_recall,
        issue_link_repo=issue_link_repo,
        integration_link_repo=integration_link_repo,
        cycle_repo=cycle_repo,
    )


def make_memory_item(node_id: str, score: float = 0.8, source_type: str = "DECISION") -> MemoryItem:
    return MemoryItem(
        source_type=source_type,
        source_id=node_id,
        node_id=node_id,
        score=score,
        snippet=f"Snippet for {node_id}",
        created_at="2024-01-01T00:00:00",
    )


def make_mock_issue_link(
    source_id: UUID,
    target_id: UUID,
    link_type: str = "related",
    target_state_group: str = "completed",
) -> MagicMock:
    from pilot_space.infrastructure.database.models.issue_link import IssueLinkType

    link = MagicMock()
    link.source_issue_id = source_id
    link.target_issue_id = target_id
    link.link_type = IssueLinkType.RELATED

    source_issue = MagicMock()
    source_issue.id = source_id
    source_issue.identifier = "PS-1"
    source_issue.name = "Source Issue"
    source_issue.state = MagicMock()
    source_issue.state.group = MagicMock()
    source_issue.state.group.value = "unstarted"

    target_issue = MagicMock()
    target_issue.id = target_id
    target_issue.identifier = "PS-2"
    target_issue.name = "Related Done Issue"
    target_issue.state = MagicMock()
    target_issue.state.group = MagicMock()
    target_issue.state.group.value = target_state_group

    link.source_issue = source_issue
    link.target_issue = target_issue

    return link


def make_mock_pr_link(issue_id: UUID, pr_url: str = "https://github.com/org/repo/pull/42") -> MagicMock:
    link = MagicMock()
    link.issue_id = issue_id
    link.external_url = pr_url
    link.link_metadata = {"state": "merged", "number": 42}
    return link


def make_mock_cycle_issue(
    issue_id: UUID | None = None,
    identifier: str = "PS-99",
    name: str = "Peer Issue",
    state_group: str = "unstarted",
) -> MagicMock:
    issue = MagicMock()
    issue.id = issue_id or uuid4()
    issue.identifier = identifier
    issue.name = name
    issue.state = MagicMock()
    issue.state.group = MagicMock()
    issue.state.group.value = state_group
    issue.assignee = None
    issue.ai_metadata = None
    return issue


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_kg_decisions_when_recall_returns_results():
    """Test 1: execute() returns enriched context with KG decisions."""
    items = [make_memory_item("node-1"), make_memory_item("node-2")]
    assembler = make_assembler(recall_items=items)
    payload = RichContextPayload(
        issue_id=uuid4(),
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    assert isinstance(result, RichContextResult)
    assert result.from_cache is False
    assert len(result.context.kg_decisions) == 2
    assert result.context.kg_decisions[0].node_id == "node-1"
    assert result.context.kg_decisions[0].source_type == "DECISION"


@pytest.mark.asyncio
async def test_execute_returns_related_prs_from_linked_closed_issues():
    """Test 2: execute() returns enriched context with related PRs when linked closed issues have PRs."""
    issue_id = uuid4()
    related_issue_id = uuid4()

    issue = make_issue_detail()
    base_context = make_base_context(issue=issue)

    # Build a link where target is the related done issue
    link = make_mock_issue_link(issue_id, related_issue_id, target_state_group="completed")

    pr_link = make_mock_pr_link(related_issue_id)

    assembler = make_assembler(
        base_context=base_context,
        issue_links=[link],
        pr_links=[pr_link],
    )
    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    assert len(result.context.related_prs) == 1
    assert result.context.related_prs[0].pr_url == "https://github.com/org/repo/pull/42"


@pytest.mark.asyncio
async def test_execute_returns_sprint_peers_when_issue_in_active_cycle():
    """Test 3: execute() returns enriched context with sprint peers when issue belongs to active cycle."""
    cycle_id = uuid4()
    issue_id = uuid4()
    issue = make_issue_detail(cycle_id=cycle_id)
    base_context = make_base_context(issue=issue)
    # Update the base context issue id to match our target issue_id
    base_context.issue.id = issue_id  # type: ignore[misc]

    peer = make_mock_cycle_issue(identifier="PS-99", name="Peer Issue")
    assembler = make_assembler(base_context=base_context, cycle_issues=[peer])

    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    assert len(result.context.sprint_peers) == 1
    assert result.context.sprint_peers[0].identifier == "PS-99"


@pytest.mark.asyncio
async def test_kg_recall_failure_returns_empty_kg_decisions_with_warning():
    """Test 4: KG recall failure logs warning and returns empty kg_decisions."""
    assembler = make_assembler(recall_raise=RuntimeError("KG unavailable"))

    payload = RichContextPayload(
        issue_id=uuid4(),
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )

    with patch("pilot_space.application.services.issue.rich_context_assembler.logger") as mock_logger:
        result = await assembler.execute(payload)
        assert mock_logger.warning.called

    assert result.context.kg_decisions == []


@pytest.mark.asyncio
async def test_all_enrichment_failures_return_base_context_unchanged():
    """Test 5: All enrichment failures still return base context unchanged."""
    base_context = make_base_context()

    assembler = make_assembler(
        base_context=base_context,
        recall_raise=RuntimeError("KG down"),
    )
    # Make issue_link_repo and integration_link_repo also fail
    assembler._issue_link_repo.find_all_for_issue = AsyncMock(
        side_effect=RuntimeError("Link repo down")
    )
    assembler._cycle_repo.get_issues_in_cycle = AsyncMock(
        side_effect=RuntimeError("Cycle repo down")
    )

    payload = RichContextPayload(
        issue_id=uuid4(),
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    # Base context fields preserved
    assert result.context.issue.identifier == "PS-1"
    assert result.context.workspace.slug == "workspace"
    assert result.context.suggested_branch == "feat/ps-1-add-oauth-login"
    # All enrichment empty
    assert result.context.kg_decisions == []
    assert result.context.related_prs == []
    assert result.context.sprint_peers == []


@pytest.mark.asyncio
async def test_budget_manager_truncates_sprint_peers_first():
    """Test 6: Budget manager truncates sprint_peers first, then related_prs, then kg_decisions."""
    # Create a context that will be huge — patch _CHAR_BUDGET to something tiny
    import pilot_space.application.services.issue.rich_context_assembler as module

    original_budget = module._CHAR_BUDGET

    try:
        # Set budget very small so truncation triggers
        module._CHAR_BUDGET = 1  # Force everything to truncate

        issue_id = uuid4()
        cycle_id = uuid4()
        issue = make_issue_detail(cycle_id=cycle_id)
        issue = IssueDetail(
            id=issue_id,
            identifier=issue.identifier,
            title=issue.title,
            description=issue.description,
            description_html=issue.description_html,
            acceptance_criteria=issue.acceptance_criteria,
            status=issue.status,
            priority=issue.priority,
            labels=issue.labels,
            state=issue.state,
            project_id=issue.project_id,
            assignee_id=issue.assignee_id,
            cycle_id=cycle_id,
        )
        base_context = make_base_context(issue=issue)
        base_context.issue.id = issue_id  # type: ignore[misc]

        peer = make_mock_cycle_issue()
        items = [make_memory_item("node-1")]

        assembler = make_assembler(
            base_context=base_context,
            recall_items=items,
            cycle_issues=[peer],
        )

        payload = RichContextPayload(
            issue_id=issue_id,
            workspace_id=uuid4(),
            requester_id=uuid4(),
        )
        result = await assembler.execute(payload)

        # When budget is 1, sprint_peers should be truncated first
        assert result.context.sprint_peers == []
    finally:
        module._CHAR_BUDGET = original_budget


@pytest.mark.asyncio
async def test_context_budget_used_pct_reflects_actual_usage():
    """Test 7: context_budget_used_pct reflects actual usage as percentage."""
    assembler = make_assembler()
    payload = RichContextPayload(
        issue_id=uuid4(),
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    assert result.context.context_budget_used_pct is not None
    assert isinstance(result.context.context_budget_used_pct, float)
    assert result.context.context_budget_used_pct >= 0.0


@pytest.mark.asyncio
async def test_kg_multiquery_deduplicates_by_node_id_keeps_highest_score():
    """Test 8: KG multi-query deduplicates by node_id, keeps highest score, limits to 10."""
    # Return duplicate node_ids with different scores from multiple queries
    # The recall mock is called multiple times (title, description, labels)
    # We simulate by having it return overlapping items
    low_score_item = make_memory_item("node-dup", score=0.3)
    high_score_item = make_memory_item("node-dup", score=0.9)
    unique_item = make_memory_item("node-unique", score=0.5)

    call_count = 0

    async def side_effect_recall(recall_payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return RecallResult(items=[low_score_item], cache_hit=False, elapsed_ms=0)
        elif call_count == 2:
            return RecallResult(items=[high_score_item, unique_item], cache_hit=False, elapsed_ms=0)
        else:
            return RecallResult(items=[], cache_hit=False, elapsed_ms=0)

    assembler = make_assembler()
    assembler._memory_recall.recall = AsyncMock(side_effect=side_effect_recall)

    payload = RichContextPayload(
        issue_id=uuid4(),
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    # Deduplicated: node-dup should have score 0.9 (highest)
    kg = result.context.kg_decisions
    dup_decisions = [d for d in kg if d.node_id == "node-dup"]
    assert len(dup_decisions) == 1
    assert dup_decisions[0].score == 0.9


@pytest.mark.asyncio
async def test_sprint_peers_exclude_target_issue():
    """Test 9: Sprint peers exclude the target issue itself."""
    issue_id = uuid4()
    cycle_id = uuid4()
    issue = make_issue_detail(cycle_id=cycle_id)
    base_context = make_base_context(issue=issue)
    base_context.issue.id = issue_id  # type: ignore[misc]

    # Cycle contains both the target issue and a peer
    target_as_peer = make_mock_cycle_issue(issue_id=issue_id, identifier="PS-1", name="Target Issue")
    actual_peer = make_mock_cycle_issue(identifier="PS-99", name="Peer Issue")

    assembler = make_assembler(
        base_context=base_context,
        cycle_issues=[target_as_peer, actual_peer],
    )

    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    # Target issue excluded
    identifiers = [p.identifier for p in result.context.sprint_peers]
    assert "PS-1" not in identifiers
    assert "PS-99" in identifiers


@pytest.mark.asyncio
async def test_related_prs_limited_to_5():
    """Test 10: Related PRs limited to 5."""
    issue_id = uuid4()
    base_context = make_base_context()
    base_context.issue.id = issue_id  # type: ignore[misc]

    # Create 8 related done issues each with a PR
    related_ids = [uuid4() for _ in range(8)]
    links = [make_mock_issue_link(issue_id, rid, target_state_group="completed") for rid in related_ids]
    pr_links = [make_mock_pr_link(rid, pr_url=f"https://github.com/org/repo/pull/{i}") for i, rid in enumerate(related_ids)]
    # Wire pr_links to their issue_ids
    for pr, rid in zip(pr_links, related_ids):
        pr.issue_id = rid

    assembler = make_assembler(
        base_context=base_context,
        issue_links=links,
        pr_links=pr_links,
    )

    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=uuid4(),
        requester_id=uuid4(),
    )
    result = await assembler.execute(payload)

    assert len(result.context.related_prs) <= 5


@pytest.mark.asyncio
async def test_second_call_returns_cached_result():
    """Test 11: Second call with same issue_id+workspace_id returns cached result."""
    issue_id = uuid4()
    workspace_id = uuid4()

    assembler = make_assembler()

    payload = RichContextPayload(
        issue_id=issue_id,
        workspace_id=workspace_id,
        requester_id=uuid4(),
    )

    result1 = await assembler.execute(payload)
    assert result1.from_cache is False

    # Second call with same key — base_service should NOT be called again
    result2 = await assembler.execute(payload)
    assert result2.from_cache is True
    assert assembler._base_service.execute.call_count == 1


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_estimate_tokens():
    """estimate_tokens returns len // 4."""
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("") == 0


def test_budget_constants():
    """Budget constants are as specified."""
    assert _CHAR_BUDGET == 480_000
    assert _TOKEN_BUDGET == 120_000
    assert _CACHE_TTL_SECONDS == 3600
