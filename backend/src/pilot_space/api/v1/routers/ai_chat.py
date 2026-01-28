"""Unified AI chat endpoint for conversational agents.

Provides a single endpoint for all AI chat interactions with streaming
responses via SSE (Server-Sent Events).

Reference: docs/architect/pilotspace-agent-architecture.md
Design Decisions: DD-058 (SSE streaming), DD-003 (Approval flow)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pilot_space.dependencies import (
    CurrentUserId,
    DbSession,
    OrchestratorDep,
    PermissionHandlerDep,
    SessionHandlerDep,
    SkillRegistryDep,
)

router = APIRouter(prefix="/ai", tags=["ai-chat"])


class ChatContext(BaseModel):
    """Context for AI chat request.

    Provides optional context about the current workspace, note, issue,
    or selected text to inform AI responses.
    """

    workspace_id: UUID = Field(..., description="Workspace ID for context")
    note_id: UUID | None = Field(None, description="Note ID if chatting within note")
    issue_id: UUID | None = Field(None, description="Issue ID if chatting about issue")
    selected_text: str | None = Field(None, description="Selected text from editor")


class ChatRequest(BaseModel):
    """Request for AI chat interaction.

    Attributes:
        message: User message to send to AI.
        session_id: Optional session ID to resume existing conversation.
        context: Context about current workspace/note/issue.
    """

    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: str | None = Field(None, description="Session ID to resume conversation")
    context: ChatContext = Field(..., description="Context for AI response")


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user_id: CurrentUserId,
    session: DbSession,
    orchestrator: OrchestratorDep,
    session_handler: SessionHandlerDep,
    permission_handler: PermissionHandlerDep,
    skill_registry: SkillRegistryDep,
) -> StreamingResponse:
    """Unified AI chat endpoint with streaming responses.

    Supports:
    - Multi-turn conversations via session_id
    - Context-aware responses (note, issue, workspace)
    - Real-time streaming via SSE
    - Tool calls with approval flow
    - Skill discovery and invocation

    Args:
        request: Chat request with message and context.
        user_id: Current user ID.
        session: Database session.
        orchestrator: SDK orchestrator for agent execution.
        session_handler: Session handler for multi-turn conversations.
        permission_handler: Permission handler for approval flow.
        skill_registry: Skill registry for skill discovery.

    Returns:
        StreamingResponse with SSE events.
    """
    from pilot_space.api.v1.middleware import extract_ai_context

    # Extract full AI context (loads Note/Issue objects if IDs provided)
    ai_context = await extract_ai_context(
        request=request,  # type: ignore[arg-type]
        session=session,
        note_id=request.context.note_id,
        issue_id=request.context.issue_id,
        workspace_id=request.context.workspace_id,
        selected_text=request.context.selected_text,
    )

    # Get or create conversation session
    conv_session = None
    if session_handler is not None:
        if request.session_id:
            # Resume existing session
            from uuid import UUID as parse_uuid

            session_id_uuid = parse_uuid(request.session_id)
            conv_session = await session_handler.get_session(session_id_uuid)
        else:
            # Create new session
            conv_session = await session_handler.create_session(
                workspace_id=request.context.workspace_id,
                user_id=user_id,
                agent_name="conversation",
            )

    # Build agent input
    agent_input = {
        "message": request.message,
        "context": ai_context,
        "session_id": conv_session.session_id if conv_session else None,
        "user_id": str(user_id),
        "workspace_id": str(request.context.workspace_id),
    }

    # Stream response from conversation agent
    async def stream_response():
        """Generate SSE stream from agent responses."""
        try:
            # Execute PilotSpaceAgent with streaming
            async for sse_chunk in _execute_agent_stream(
                orchestrator,
                agent_name="conversation",
                input_data=agent_input,
                context=ai_context,
            ):
                # Events are already SSE-formatted by PilotSpaceAgent.stream()
                # including message_start, text_delta, and message_stop events
                yield sse_chunk

        except Exception as e:
            # Send error event in SSE format
            import json

            error_data = {"type": "error", "error_type": "internal_error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def _execute_agent_stream(
    orchestrator: Any,
    agent_name: str,
    input_data: dict[str, Any],
    context: dict[str, Any],
):
    """Execute PilotSpaceAgent with streaming output.

    Bridges the FastAPI endpoint to PilotSpaceAgent.stream() method.

    Args:
        orchestrator: SDK orchestrator instance
        agent_name: Agent name (should be "conversation" for PilotSpaceAgent)
        input_data: Dict with message, context, session_id, user_id, workspace_id
        context: AI context dict (currently unused, included for compatibility)

    Yields:
        SSE-formatted strings from PilotSpaceAgent
    """
    from uuid import UUID as parse_uuid

    from pilot_space.ai.agents.pilotspace_agent import ChatInput, PilotSpaceAgent
    from pilot_space.ai.agents.sdk_base import AgentContext

    # Get PilotSpaceAgent from orchestrator
    # Try multiple possible names for compatibility
    agent = orchestrator.get_agent("conversation")
    if agent is None:
        agent = orchestrator.get_agent("pilotspace_agent")
    if agent is None:
        yield "data: {'type': 'error', 'message': 'PilotSpaceAgent not registered in orchestrator'}\n\n"
        return

    if not isinstance(agent, PilotSpaceAgent):
        yield "data: {'type': 'error', 'message': 'Agent is not PilotSpaceAgent instance'}\n\n"
        return

    # Build ChatInput from input_data
    chat_input = ChatInput(
        message=input_data["message"],
        session_id=parse_uuid(input_data["session_id"]) if input_data.get("session_id") else None,
        context=input_data.get("context", {}),
        user_id=parse_uuid(input_data["user_id"]) if input_data.get("user_id") else None,
        workspace_id=parse_uuid(input_data["workspace_id"])
        if input_data.get("workspace_id")
        else None,
    )

    # Build AgentContext
    agent_context = AgentContext(
        workspace_id=parse_uuid(input_data["workspace_id"]),
        user_id=parse_uuid(input_data["user_id"]),
    )

    # Stream events (already SSE-formatted by PilotSpaceAgent)
    async for sse_chunk in agent.stream(chat_input, agent_context):
        yield sse_chunk
