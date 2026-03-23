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

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status

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
from pilot_space.application.services.memory.memory_search_service import (
    MemorySearchPayload,
    MemorySearchService,
)
from pilot_space.config import get_settings
from pilot_space.dependencies.auth import SessionDep, require_workspace_member
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue service not configured",
        )

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
            rules=rule_inputs,
        )
    )

    return ConstitutionIngestResponse(
        version=result.version,
        rule_count=result.rule_count,
        indexing_enqueued=result.indexing_enqueued,
    )
