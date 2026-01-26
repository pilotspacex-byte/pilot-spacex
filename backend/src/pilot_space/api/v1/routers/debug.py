"""Debug endpoints for development mode.

IMPORTANT: These endpoints are ONLY available in development mode.
They provide introspection into mock AI responses and system state.

Endpoints:
- GET /debug/mock-status: Check if mock mode is enabled
- GET /debug/mock-calls: View mock AI call history
- POST /debug/mock-calls/clear: Clear mock call history
- GET /debug/mock-generators: List registered mock generators
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from pilot_space.ai.providers.mock import MockProvider, MockResponseRegistry
from pilot_space.config import get_settings

router = APIRouter(prefix="/debug", tags=["debug"])


def _ensure_development() -> None:
    """Ensure we're in development mode.

    Raises:
        HTTPException: If not in development mode.
    """
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode",
        )


@router.get("/mock-status")
async def get_mock_status() -> dict[str, Any]:
    """Get current mock mode status.

    Returns:
        Dict with:
        - enabled: Whether mock mode is active
        - app_env: Current application environment
        - ai_fake_mode: AI_FAKE_MODE setting value
        - ai_fake_latency_ms: Simulated latency in milliseconds
        - ai_fake_streaming_chunk_delay_ms: Streaming chunk delay
    """
    _ensure_development()

    settings = get_settings()
    mock_provider = MockProvider.get_instance()

    return {
        "enabled": mock_provider.is_enabled(),
        "app_env": settings.app_env,
        "ai_fake_mode": settings.ai_fake_mode,
        "ai_fake_latency_ms": settings.ai_fake_latency_ms,
        "ai_fake_streaming_chunk_delay_ms": settings.ai_fake_streaming_chunk_delay_ms,
    }


@router.get("/mock-calls")
async def get_mock_calls() -> dict[str, Any]:
    """Get history of mock AI calls.

    Returns:
        Dict with:
        - calls: List of mock call records
        - total: Total number of calls in history
    """
    _ensure_development()

    history = MockResponseRegistry.get_history()

    return {
        "calls": [record.to_dict() for record in history],
        "total": len(history),
    }


@router.post("/mock-calls/clear")
async def clear_mock_calls() -> dict[str, str]:
    """Clear mock call history.

    Returns:
        Success message.
    """
    _ensure_development()

    MockResponseRegistry.clear_history()

    return {
        "message": "Mock call history cleared successfully",
    }


@router.get("/mock-generators")
async def get_mock_generators() -> dict[str, Any]:
    """List all registered mock generators.

    Returns:
        Dict with:
        - generators: List of registered agent names
        - total: Total number of registered generators
    """
    _ensure_development()

    registered = MockResponseRegistry.list_registered()

    return {
        "generators": registered,
        "total": len(registered),
    }


@router.post("/mock-invoke/{agent_name}")
async def invoke_mock_generator(
    agent_name: str,
    input_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke a mock generator directly without database dependencies.

    This endpoint allows testing mock AI responses during development
    without needing a full database setup.

    Args:
        agent_name: Name of the agent to test (e.g., "GhostTextAgent")
        input_data: Optional input data to pass to the generator

    Returns:
        Dict with:
        - agent_name: The requested agent name
        - input_data: The input that was provided
        - output: The mock response generated
        - mock_enabled: Whether mock mode is enabled
    """
    _ensure_development()

    # Check if mock mode is enabled
    mock_provider = MockProvider.get_instance()
    if not mock_provider.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mock mode is not enabled. Set AI_FAKE_MODE=true in development.",
        )

    # Check if generator exists
    generator = MockResponseRegistry.get_generator(agent_name)
    if generator is None:
        registered = MockResponseRegistry.list_registered()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mock generator for '{agent_name}'. Available: {registered}",
        )

    # Generate mock response
    test_input = input_data or {}
    output = generator(test_input)

    return {
        "agent_name": agent_name,
        "input_data": test_input,
        "output": output,
        "mock_enabled": True,
    }


__all__ = ["router"]
