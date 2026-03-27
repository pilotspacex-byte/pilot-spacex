"""Pydantic schemas for the top-level AI router.

These are deprecated schemas kept for backward-compatible endpoints
that remain in ai.py while newer sub-routers provide typed responses.

T096: AI router implementation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """DEPRECATED: Chat request schema."""

    message: str = Field(description="User message")
    context: dict[str, Any] | None = Field(default=None, description="Optional context")


class ChatResponse(BaseModel):
    """DEPRECATED: Chat response schema."""

    response: str = Field(description="AI response")


class HealthResponse(BaseModel):
    """DEPRECATED: Health check response schema."""

    status: str = Field(description="Overall status")
    providers: dict[str, Any] = Field(description="Provider status details")


__all__ = ["ChatRequest", "ChatResponse", "HealthResponse"]
