"""RichContextAssembler — wraps GetImplementContextService with enrichment layers.

Phase 74 — Rich Context Engine (CTX-01..05)

Adds three enrichment layers on top of the base implement context:
1. KG decisions / patterns (memory_recall, multi-query, deduplicated)
2. Related PRs (issue links → done issues → PR URLs)
3. Sprint peers (cycle issues, excluding the target issue)

A 60% token budget cap (480k chars) enforces context window safety.
A 1-hour TTL cache prevents redundant enrichment for repeated calls.

Import note: ImplementContextResponse is imported inside execute() to avoid
a circular dependency through the api.v1 package (same pattern as
GetImplementContextService).
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from uuid import UUID

    from pilot_space.application.services.issue.get_implement_context_service import (
        GetImplementContextService,
    )
    from pilot_space.application.services.memory.memory_recall_service import (
        MemoryItem,
        MemoryRecallService,
    )
    from pilot_space.infrastructure.database.repositories.cycle_repository import (
        CycleRepository,
    )
    from pilot_space.infrastructure.database.repositories.integration_link_repository import (
        IntegrationLinkRepository,
    )
    from pilot_space.infrastructure.database.repositories.issue_link_repository import (
        IssueLinkRepository,
    )

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4
_CONTEXT_WINDOW = 200_000
_BUDGET_FRACTION = 0.60
_TOKEN_BUDGET = int(_CONTEXT_WINDOW * _BUDGET_FRACTION)  # 120_000
_CHAR_BUDGET = _TOKEN_BUDGET * _CHARS_PER_TOKEN  # 480_000
_MAX_KG_ITEMS = 10
_MAX_RELATED_PRS = 5
_MAX_SPRINT_PEERS = 10
_AC_SUMMARY_CHARS = 200
_CACHE_TTL_SECONDS = 3600  # 1-hour TTL per locked decision (reuse GenerateAIContextService pattern)
_CACHE_MAX_SIZE = 128  # Max cached issue contexts


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count (4 chars per token heuristic)."""
    return len(text) // _CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Payload / Result
# ---------------------------------------------------------------------------


@dataclass
class RichContextPayload:
    """Input for RichContextAssembler.execute."""

    issue_id: UUID
    workspace_id: UUID
    requester_id: UUID


@dataclass
class RichContextResult:
    """Output from RichContextAssembler.execute."""

    context: Any  # ImplementContextResponse at runtime
    from_cache: bool = False


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RichContextAssembler:
    """Wraps GetImplementContextService with three enrichment layers.

    Enrichment layers (run concurrently via asyncio.gather):
    1. KG decisions — recall from knowledge graph using multi-query strategy
    2. Related PRs — traverse issue links to find PRs from done related issues
    3. Sprint peers — list other active issues in the same cycle

    Budget:
    - Total context capped at 60% of 200k token window = 480k chars
    - If over budget: truncate sprint_peers first, then related_prs, then kg_decisions

    Cache:
    - Class-level TTLCache with 1-hour TTL keyed by (issue_id, workspace_id)
    - Second call with same payload returns cached result immediately
    """

    _cache: TTLCache[tuple[str, str], Any] = TTLCache(maxsize=_CACHE_MAX_SIZE, ttl=_CACHE_TTL_SECONDS)

    def __init__(
        self,
        base_service: GetImplementContextService,
        memory_recall: MemoryRecallService,
        issue_link_repo: IssueLinkRepository,
        integration_link_repo: IntegrationLinkRepository,
        cycle_repo: CycleRepository,
    ) -> None:
        """Initialize with injected dependencies."""
        self._base_service = base_service
        self._memory_recall = memory_recall
        self._issue_link_repo = issue_link_repo
        self._integration_link_repo = integration_link_repo
        self._cycle_repo = cycle_repo

    async def execute(self, payload: RichContextPayload) -> RichContextResult:
        """Assemble enriched implement context for an issue.

        Steps:
        1. Check TTL cache.
        2. Call base service to get base context.
        3. Fan out three enrichment queries concurrently.
        4. Apply budget truncation.
        5. Build enriched response and cache it.
        """
        # 1. Cache check
        cache_key = (str(payload.issue_id), str(payload.workspace_id))
        if cache_key in self._cache:
            return RichContextResult(context=self._cache[cache_key], from_cache=True)

        # 2. Deferred import — avoid circular import through api.v1.__init__
        from pilot_space.api.v1.schemas.implement_context import (
            ImplementContextResponse,
            KGDecision,
            RelatedPR,
            SprintPeer,
        )
        from pilot_space.application.services.issue.get_implement_context_service import (
            GetImplementContextPayload,
        )

        # 3. Get base context
        base_result = await self._base_service.execute(
            GetImplementContextPayload(
                issue_id=payload.issue_id,
                workspace_id=payload.workspace_id,
                requester_id=payload.requester_id,
            )
        )
        base_context = base_result.context
        issue_detail = base_context.issue

        # 4. Fan out enrichment queries concurrently
        kg_task = self._recall_kg_context(payload, issue_detail)
        pr_task = self._fetch_related_prs(payload, issue_detail)
        sprint_task = self._fetch_sprint_peers(payload, issue_detail)

        raw_results = await asyncio.gather(kg_task, pr_task, sprint_task, return_exceptions=True)

        # 5. Handle failures with graceful degradation
        kg_decisions: list[KGDecision] = []
        related_prs: list[RelatedPR] = []
        sprint_peers: list[SprintPeer] = []

        kg_raw, pr_raw, sprint_raw = raw_results

        if isinstance(kg_raw, BaseException):
            logger.warning(
                "rich_context: KG recall failed, returning empty kg_decisions: %s",
                kg_raw,
            )
        else:
            kg_decisions = [
                KGDecision(
                    node_id=item.node_id,
                    snippet=item.snippet,
                    score=item.score,
                    source_type=item.source_type,
                )
                for item in kg_raw
            ]

        if isinstance(pr_raw, BaseException):
            logger.warning(
                "rich_context: PR fetch failed, returning empty related_prs: %s",
                pr_raw,
            )
        else:
            related_prs = [
                RelatedPR(
                    issue_identifier=item["issue_identifier"],
                    issue_title=item["issue_title"],
                    pr_url=item["pr_url"],
                    pr_state=item.get("pr_state"),
                )
                for item in pr_raw
            ]

        if isinstance(sprint_raw, BaseException):
            logger.warning(
                "rich_context: Sprint peer fetch failed, returning empty sprint_peers: %s",
                sprint_raw,
            )
        else:
            sprint_peers = [
                SprintPeer(
                    identifier=item["identifier"],
                    title=item["title"],
                    state=item["state"],
                    assignee_name=item.get("assignee_name"),
                    acceptance_criteria_summary=item.get("acceptance_criteria_summary"),
                )
                for item in sprint_raw
            ]

        # 6. Budget management — calculate total chars, truncate in priority order
        base_chars = len(base_context.model_dump_json())

        def enrichment_chars() -> int:
            total = base_chars
            try:
                total += len(json.dumps([d.model_dump() for d in kg_decisions]))
            except Exception:
                pass
            try:
                total += len(json.dumps([p.model_dump() for p in related_prs]))
            except Exception:
                pass
            try:
                total += len(json.dumps([s.model_dump() for s in sprint_peers]))
            except Exception:
                pass
            return total

        total_chars = enrichment_chars()

        if total_chars > _CHAR_BUDGET:
            # Truncate sprint_peers first (lowest priority)
            sprint_peers = []
            total_chars = base_chars + len(
                json.dumps([d.model_dump() for d in kg_decisions])
            ) + len(json.dumps([p.model_dump() for p in related_prs]))

        if total_chars > _CHAR_BUDGET:
            # Truncate related_prs next
            related_prs = []
            total_chars = base_chars + len(json.dumps([d.model_dump() for d in kg_decisions]))

        if total_chars > _CHAR_BUDGET:
            # Truncate kg_decisions last
            kg_decisions = []
            total_chars = base_chars

        # 7. Compute budget percentage
        context_budget_used_pct = round((total_chars / _CHAR_BUDGET) * 100, 1)

        # 8. Build enriched response
        enriched = ImplementContextResponse(
            issue=base_context.issue,
            linked_notes=base_context.linked_notes,
            repository=base_context.repository,
            workspace=base_context.workspace,
            project=base_context.project,
            suggested_branch=base_context.suggested_branch,
            kg_decisions=kg_decisions,
            related_prs=related_prs,
            sprint_peers=sprint_peers,
            context_budget_used_pct=context_budget_used_pct,
        )

        # 9. Cache and return
        self._cache[cache_key] = enriched
        return RichContextResult(context=enriched, from_cache=False)

    # -------------------------------------------------------------------------
    # Private enrichment methods
    # -------------------------------------------------------------------------

    async def _recall_kg_context(
        self,
        payload: RichContextPayload,
        issue_detail: Any,
    ) -> list[MemoryItem]:
        """Recall KG decisions/patterns using multi-query strategy.

        Queries:
        - Issue title
        - Issue description (first 200 chars)
        - Issue labels (joined)

        Results are deduplicated by node_id (highest score wins),
        sorted by score descending, limited to _MAX_KG_ITEMS.
        """
        from pilot_space.application.services.memory.memory_recall_service import RecallPayload

        queries: list[str] = []

        title = (issue_detail.title or "").strip()
        if title:
            queries.append(title)

        description = (issue_detail.description or "")[:200].strip()
        if description:
            queries.append(description)

        label_names = " ".join(
            getattr(label, "name", "") for label in (issue_detail.labels or [])
        ).strip()
        if label_names:
            queries.append(label_names)

        if not queries:
            return []

        # Fan out recall calls concurrently
        recall_tasks = [
            self._memory_recall.recall(
                RecallPayload(
                    workspace_id=payload.workspace_id,
                    query=q,
                    k=10,
                    min_score=0.0,
                )
            )
            for q in queries
        ]
        raw_results = await asyncio.gather(*recall_tasks, return_exceptions=True)

        # Merge and deduplicate by node_id (keep highest score)
        best_by_node: dict[str, MemoryItem] = {}
        for res in raw_results:
            if isinstance(res, BaseException):
                logger.warning("rich_context: single KG query failed: %s", res)
                continue
            for item in res.items:
                existing = best_by_node.get(item.node_id)
                if existing is None or item.score > existing.score:
                    best_by_node[item.node_id] = item

        # Sort by score descending, take top _MAX_KG_ITEMS
        sorted_items = sorted(best_by_node.values(), key=lambda x: x.score, reverse=True)
        return sorted_items[:_MAX_KG_ITEMS]

    async def _fetch_related_prs(
        self,
        payload: RichContextPayload,
        issue_detail: Any,
    ) -> list[dict[str, Any]]:
        """Fetch PRs from related done issues.

        Steps:
        1. Get all issue links (bidirectional).
        2. Filter to RELATED, BLOCKS, BLOCKED_BY link types.
        3. Collect related issue objects and IDs (done states only).
        4. Batch query PRs for done issues.
        5. Build RelatedPR dicts, limited to _MAX_RELATED_PRS.
        """
        from pilot_space.infrastructure.database.models.issue_link import IssueLinkType

        _DONE_STATES = {"completed", "cancelled"}
        _RELEVANT_LINK_TYPES = {IssueLinkType.RELATED, IssueLinkType.BLOCKS, IssueLinkType.BLOCKED_BY}

        links = await self._issue_link_repo.find_all_for_issue(
            payload.issue_id,
            payload.workspace_id,
        )

        # Build map of related issue id → issue object for done issues
        done_issues: dict[str, Any] = {}

        for link in links:
            if link.link_type not in _RELEVANT_LINK_TYPES:
                continue

            # Determine the "other" issue in the link
            if str(link.source_issue_id) == str(payload.issue_id):
                other_issue = link.target_issue
            else:
                other_issue = link.source_issue

            if other_issue is None:  # type: ignore[comparison-overlap]  # noload relation is None at runtime when not fetched
                continue

            state_group_value = ""
            other_state = getattr(other_issue, "state", None)
            if other_state is not None:
                state_group_value = getattr(getattr(other_state, "group", None), "value", "") or ""

            if state_group_value in _DONE_STATES:
                done_issues[str(other_issue.id)] = other_issue

        if not done_issues:
            return []

        from uuid import UUID as _UUID

        done_issue_ids = [_UUID(id_str) for id_str in done_issues]
        pr_links = await self._integration_link_repo.get_pull_requests_for_issues(
            done_issue_ids,
            payload.workspace_id,
        )

        results: list[dict[str, Any]] = []
        for pr in pr_links:
            if len(results) >= _MAX_RELATED_PRS:
                break

            issue_id_str = str(getattr(pr, "issue_id", ""))
            related_issue = done_issues.get(issue_id_str)
            if related_issue is None:
                continue

            pr_url = getattr(pr, "external_url", None) or ""
            metadata = getattr(pr, "link_metadata", None) or {}
            pr_state = metadata.get("state") if isinstance(metadata, dict) else None

            results.append(
                {
                    "issue_identifier": related_issue.identifier,
                    "issue_title": related_issue.name,
                    "pr_url": pr_url,
                    "pr_state": pr_state,
                }
            )

        return results

    async def _fetch_sprint_peers(
        self,
        payload: RichContextPayload,
        issue_detail: Any,
    ) -> list[dict[str, Any]]:
        """Fetch other active issues in the same sprint/cycle.

        Returns empty list if issue has no cycle_id.
        Excludes the target issue itself.
        Limited to _MAX_SPRINT_PEERS.
        """
        cycle_id = getattr(issue_detail, "cycle_id", None)
        if cycle_id is None:
            return []

        cycle_issues = await self._cycle_repo.get_issues_in_cycle(
            cycle_id,
            include_completed=False,
        )

        results: list[dict[str, Any]] = []
        for peer in cycle_issues:
            if len(results) >= _MAX_SPRINT_PEERS:
                break

            if str(peer.id) == str(payload.issue_id):
                continue

            state_value = "unknown"
            peer_state = getattr(peer, "state", None)
            if peer_state is not None:
                state_value = getattr(getattr(peer_state, "group", None), "value", "unknown")

            assignee_name: str | None = None
            peer_assignee = getattr(peer, "assignee", None)
            if peer_assignee is not None:
                assignee_name = getattr(peer_assignee, "display_name", None)

            # First acceptance criterion, truncated
            ac_summary: str | None = None
            ai_metadata = getattr(peer, "ai_metadata", None) or {}
            if isinstance(ai_metadata, dict):
                ac_list = ai_metadata.get("acceptance_criteria", [])
                if ac_list:
                    ac_summary = str(ac_list[0])[:_AC_SUMMARY_CHARS]

            results.append(
                {
                    "identifier": peer.identifier,
                    "title": peer.name,
                    "state": state_value,
                    "assignee_name": assignee_name,
                    "acceptance_criteria_summary": ac_summary,
                }
            )

        return results


__all__ = [
    "RichContextAssembler",
    "RichContextPayload",
    "RichContextResult",
    "estimate_tokens",
]
