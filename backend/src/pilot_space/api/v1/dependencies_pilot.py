"""FastAPI dependency type aliases for pilot CLI services.

Kept in a separate module to respect the 700-line limit on dependencies.py.
"""

from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, Request, status

from pilot_space.api.v1.repository_deps import PilotAPIKeyRepositoryDep
from pilot_space.application.services.auth import ValidateAPIKeyService
from pilot_space.application.services.issue import GetImplementContextService
from pilot_space.application.services.issue.rich_context_assembler import RichContextAssembler
from pilot_space.container import Container
from pilot_space.dependencies.auth import SessionDep, get_current_user, get_token_from_header
from pilot_space.dependencies.workspace import get_current_workspace_id

__all__ = [
    "CLIRequesterContextDep",
    "GetImplementContextServiceDep",
    "RichContextAssemblerDep",
    "ValidateAPIKeyServiceDep",
]


@inject
def _get_implement_context_service(
    svc: GetImplementContextService = Depends(Provide[Container.get_implement_context_service]),
) -> GetImplementContextService:
    return svc


GetImplementContextServiceDep = Annotated[
    GetImplementContextService, Depends(_get_implement_context_service)
]


@inject
def _get_rich_context_assembler(
    svc: RichContextAssembler = Depends(Provide[Container.rich_context_assembler]),
) -> RichContextAssembler:
    return svc


RichContextAssemblerDep = Annotated[RichContextAssembler, Depends(_get_rich_context_assembler)]


@inject
def _get_validate_api_key_service(
    svc: ValidateAPIKeyService = Depends(Provide[Container.validate_api_key_service]),
) -> ValidateAPIKeyService:
    return svc


ValidateAPIKeyServiceDep = Annotated[ValidateAPIKeyService, Depends(_get_validate_api_key_service)]


async def _get_cli_requester_context(
    request: Request,
    _session: SessionDep,
    api_key_repo: PilotAPIKeyRepositoryDep,
) -> tuple[UUID, UUID]:
    """Resolve (user_id, workspace_id) from Supabase JWT or Pilot API key.

    Authentication order:
    1. If the bearer token contains no dots, treat it as a Pilot API key.
       Validates against pilot_api_keys table; derives user_id + workspace_id
       from the key record — no X-Workspace-Id header required.
    2. Otherwise, validate as a Supabase JWT and require X-Workspace-Id header
       (standard web-browser path).

    Args:
        request: Incoming HTTP request.
        _session: Database session (establishes ContextVar for repositories).
        api_key_repo: Repository for pilot_api_keys lookup.

    Returns:
        (user_id, workspace_id) tuple.

    Raises:
        HTTPException 401: If neither JWT nor API key authentication succeeds.
        HTTPException 400: If JWT path is used but X-Workspace-Id is missing.
    """
    try:
        token = get_token_from_header(request)
    except HTTPException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Pilot API keys are opaque strings (no dots); JWTs are header.payload.sig
    if "." not in token:
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = await api_key_repo.get_by_key_hash(key_hash)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        await api_key_repo.mark_last_used(api_key.id)
        return api_key.user_id, api_key.workspace_id

    # JWT path — validate token, then require workspace header
    user = get_current_user(request)
    workspace_id = get_current_workspace_id(request)
    return user.user_id, workspace_id


CLIRequesterContextDep = Annotated[tuple[UUID, UUID], Depends(_get_cli_requester_context)]
