"""Backward-compatibility shim for the AI proxy router.

The proxy endpoints have been extracted into a standalone FastAPI
sub-application at ``pilot_space.ai.proxy.app``.  This module re-exports
the key symbols so that existing test patches (which target
``pilot_space.api.v1.routers.ai_proxy.*``) continue to resolve.

The ``router`` object is no longer included in the main app via
``include_router`` -- the sub-app is mounted directly in ``main.py``.
"""

from __future__ import annotations

from fastapi import APIRouter

from pilot_space.ai.proxy.app import (
    get_cached_client,
    get_cached_openai_client,
    proxy_embeddings,
    proxy_messages,
    validate_tenant,
)

# Kept for any code that still imports ``from ...ai_proxy import router``
router = APIRouter(tags=["ai-proxy"])

__all__ = [
    "get_cached_client",
    "get_cached_openai_client",
    "proxy_embeddings",
    "proxy_messages",
    "router",
    "validate_tenant",
]
