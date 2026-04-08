"""Memory API router.

T-036: Memory engine endpoints.

POST /api/v1/workspaces/{workspace_id}/ai/memory/search
GET  /api/v1/workspaces/{workspace_id}/ai/memory/constitution/version
POST /api/v1/workspaces/{workspace_id}/ai/memory/constitution/ingest

Feature 015: AI Workforce Platform — Memory Engine
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response, status
from pydantic import BaseModel, Field

from pilot_space.api.v1.dependencies import (
    MemoryLifecycleServiceDep,
    MemoryRecallServiceDep,
)
from pilot_space.api.v1.schemas.memory import (
    ConstitutionIngestRequest,
    ConstitutionIngestResponse,
    ConstitutionVersionResponse,
    MemorySearchEntry,
    MemorySearchRequest,
    MemorySearchResponse,
)
from pilot_space.application.services.memory.constitution_service import (
    ConstitutionIngestPayload,
    ConstitutionIngestService,
    ConstitutionRuleInput,
)
from pilot_space.application.services.memory.memory_lifecycle_service import (
    ForgetPayload,
    GDPRForgetPayload,
    PinPayload,
)
from pilot_space.application.services.memory.memory_recall_service import RecallPayload
from pilot_space.application.services.memory.memory_search_service import (
    MemorySearchPayload,
    MemorySearchService,
)
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import (
    CurrentUser,
    DbSession,
    SessionDep,
    WorkspaceAdminId,
    WorkspaceMemberId,
    require_workspace_member,
)
from pilot_space.domain.exceptions import ServiceUnavailableError
from pilot_space.domain.memory.memory_type import MemoryType
from pilot_space.infrastructure.database.repositories.constitution_repository import (
    ConstitutionRuleRepository,
)
from pilot_space.infrastructure.database.repositories.memory_repository import (
    MemoryEntryRepository,
)
from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

WorkspaceIdPath = Annotated[UUID, Path(description="Workspace UUID")]


@router.post(
    "/workspaces/{workspace_id}/ai/memory/search",
    response_model=MemorySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid memory search",
    description=(
        "Search workspace memory using hybrid vector + full-text fusion scoring. "
        "<200ms SLA at 1000 entries. Falls back to keyword-only if Gemini unavailable."
    ),
)
async def search_memory(
    workspace_id: WorkspaceIdPath,
    request: MemorySearchRequest,
    session: SessionDep,
    response: Response,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> MemorySearchResponse:
    """Search workspace memory entries with hybrid scoring."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = '</api/v1/knowledge-graph/search>; rel="successor-version"'

    settings = get_settings()
    google_api_key = settings.google_api_key.get_secret_value() if settings.google_api_key else None

    memory_repo = MemoryEntryRepository(session)
    service = MemorySearchService(memory_repo, session)

    result = await service.execute(
        MemorySearchPayload(
            query=request.query,
            workspace_id=workspace_id,
            limit=request.limit,
            google_api_key=google_api_key,
        )
    )

    entries = [
        MemorySearchEntry(
            id=str(row.get("id", "")),
            content=str(row.get("content", "")),
            source_type=str(row.get("source_type", "")),
            pinned=bool(row.get("pinned", False)),
            score=float(row.get("score", 0.0)),
            embedding_score=float(row.get("embedding_score", 0.0)),
            text_score=float(row.get("text_score", 0.0)),
        )
        for row in result.results
    ]

    return MemorySearchResponse(
        results=entries,
        query=result.query,
        embedding_used=result.embedding_used,
        count=len(entries),
    )


@router.get(
    "/workspaces/{workspace_id}/ai/memory/constitution/version",
    response_model=ConstitutionVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current constitution version",
    description="Returns the latest constitution version for the workspace.",
)
async def get_constitution_version(
    workspace_id: WorkspaceIdPath,
    session: SessionDep,
    response: Response,
    _member: Annotated[UUID, Depends(require_workspace_member)],
) -> ConstitutionVersionResponse:
    """Get the current constitution version for the workspace."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = (
        '</api/v1/knowledge-graph/constitution/version>; rel="successor-version"'
    )

    const_repo = ConstitutionRuleRepository(session)
    version = await const_repo.get_latest_version(workspace_id)

    return ConstitutionVersionResponse(
        version=version,
        workspace_id=workspace_id,
    )


@router.post(
    "/workspaces/{workspace_id}/ai/memory/constitution/ingest",
    response_model=ConstitutionIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest constitution rules",
    description=(
        "Ingest workspace AI behavior rules. Parses RFC 2119 severity, bumps version, "
        "persists synchronously, enqueues async vector indexing (<30s typical)."
    ),
)
async def ingest_constitution(
    workspace_id: WorkspaceIdPath,
    request: ConstitutionIngestRequest,
    fastapi_request: Request,
    session: SessionDep,
    response: Response,
    _member: Annotated[UUID, Depends(require_workspace_member)],
    current_user: CurrentUser,
) -> ConstitutionIngestResponse:
    """Ingest workspace constitution rules as a new version."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = (
        '</api/v1/knowledge-graph/constitution/ingest>; rel="successor-version"'
    )

    const_repo = ConstitutionRuleRepository(session)

    queue = fastapi_request.app.state.container.queue_client()
    if queue is None:
        raise ServiceUnavailableError("Queue service not configured")

    service = ConstitutionIngestService(const_repo, queue, session)

    rule_inputs = [
        ConstitutionRuleInput(
            content=r.content,
            severity=r.severity,
            source_block_id=r.source_block_id,
        )
        for r in request.rules
    ]

    result = await service.execute(
        ConstitutionIngestPayload(
            workspace_id=workspace_id,
            actor_user_id=current_user.user_id,
            rules=rule_inputs,
        )
    )

    return ConstitutionIngestResponse(
        version=result.version,
        rule_count=result.rule_count,
        indexing_enqueued=result.indexing_enqueued,
    )


# ---------------------------------------------------------------------------
# Phase 69 / 69-05-03 — recall + lifecycle (pin / forget / GDPR forget)
# ---------------------------------------------------------------------------


class RecallRequest(BaseModel):
    """Body for ``POST /workspaces/{workspace_id}/ai/memory/recall``."""

    query: str = Field(..., min_length=1)
    k: int = Field(default=8, ge=1, le=50)
    types: list[str] | None = None
    min_score: float = Field(default=0.7, ge=0.0, le=1.0)


class MemoryItemResponse(BaseModel):
    id: str
    type: str
    score: float
    content: str
    source_id: str | None = None
    source_type: str | None = None


class RecallResponse(BaseModel):
    items: list[MemoryItemResponse]
    cache_hit: bool
    elapsed_ms: int


class GdprForgetRequest(BaseModel):
    user_id: UUID


class SuccessResponse(BaseModel):
    success: bool


@router.post(
    "/workspaces/{workspace_id}/ai/memory/recall",
    response_model=RecallResponse,
    summary="Semantic memory recall",
)
async def recall_memory(
    workspace_id: WorkspaceMemberId,
    body: RecallRequest,
    current_user: CurrentUser,
    session: DbSession,
    service: MemoryRecallServiceDep,
) -> RecallResponse:
    """Hybrid semantic recall over the workspace knowledge graph."""
    _ = session  # ContextVar population — required for DI session lookup.

    types_tuple: tuple[MemoryType, ...] | None = None
    if body.types is not None:
        types_tuple = tuple(MemoryType(t) for t in body.types)

    result = await service.recall(
        RecallPayload(
            workspace_id=workspace_id,
            query=body.query,
            k=body.k,
            types=types_tuple,
            min_score=body.min_score,
            user_id=current_user.user_id,
        )
    )
    return RecallResponse(
        items=[
            MemoryItemResponse(
                id=item.node_id,
                type=item.source_type,
                score=item.score,
                content=item.snippet,
                source_id=item.source_id,
                source_type=item.source_type,
            )
            for item in result.items
        ],
        cache_hit=result.cache_hit,
        elapsed_ms=int(result.elapsed_ms),
    )


@router.post(
    "/workspaces/{workspace_id}/ai/memory/{memory_id}/pin",
    response_model=SuccessResponse,
    summary="Pin a memory node",
)
async def pin_memory(
    workspace_id: WorkspaceAdminId,
    memory_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: MemoryLifecycleServiceDep,
) -> SuccessResponse:
    """Pin a memory node so it survives decay sweeps. Admin-only."""
    _ = session
    await service.pin(
        PinPayload(
            workspace_id=workspace_id,
            node_id=memory_id,
            actor_user_id=current_user.user_id,
        )
    )
    return SuccessResponse(success=True)


@router.delete(
    "/workspaces/{workspace_id}/ai/memory/{memory_id}",
    response_model=SuccessResponse,
    summary="Forget (soft-delete) a memory node",
)
async def forget_memory(
    workspace_id: WorkspaceAdminId,
    memory_id: UUID,
    current_user: CurrentUser,
    session: DbSession,
    service: MemoryLifecycleServiceDep,
) -> SuccessResponse:
    """Soft-delete a memory node. Admin-only."""
    _ = session
    await service.forget(
        ForgetPayload(
            workspace_id=workspace_id,
            node_id=memory_id,
            actor_user_id=current_user.user_id,
        )
    )
    return SuccessResponse(success=True)


@router.post(
    "/workspaces/{workspace_id}/ai/memory/gdpr-forget-user",
    response_model=SuccessResponse,
    summary="GDPR hard-delete all memories for a user",
)
async def gdpr_forget_user(
    workspace_id: WorkspaceAdminId,
    body: GdprForgetRequest,
    session: DbSession,
    service: MemoryLifecycleServiceDep,
) -> SuccessResponse:
    """Hard-delete every memory node owned by ``user_id``. Admin-only.

    Note: ``workspace_id`` from the path is intentionally NOT forwarded to
    the service. ``MemoryLifecycleService.gdpr_forget_user`` is a global
    hard delete keyed only on ``user_id`` (per its docstring); admin
    authorization on the enclosing workspace is the actual access guard
    for this endpoint.
    """
    _ = session
    _ = workspace_id  # admin auth guard only; service is global-scope
    await service.gdpr_forget_user(GDPRForgetPayload(user_id=body.user_id))
    return SuccessResponse(success=True)
