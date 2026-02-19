"""PilotSpace Agent - Centralized orchestrator."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient, Message

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.agents.pilotspace_agent_helpers import (
    ALL_TOOL_NAMES,
    build_contextual_message,
    build_subagent_definitions,
    has_skill_files,
    transform_sdk_message as transform_sdk_message_helper,
)
from pilot_space.ai.agents.pilotspace_intent_pipeline import (
    PILOTSPACE_SYSTEM_PROMPT_BASE,
    ConfirmationBus,
    build_memory_context_prefix,
    recall_workspace_context,
    run_intent_pipeline_step,
    save_skill_outcome_to_memory,
)
from pilot_space.ai.agents.pilotspace_stream_utils import (
    build_dynamic_system_prompt,
    build_mcp_servers,
    capture_content_from_sse,
    classify_effort,
    detect_skill_from_message,
    estimate_tokens,
    merge_sdk_and_queue,
    save_session_messages,
)
from pilot_space.ai.agents.role_skill_materializer import materialize_role_skills
from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.sdk.sandbox_config import ModelTier, configure_sdk_for_space
from pilot_space.infrastructure.logging import get_logger
from pilot_space.spaces.manager import SpaceManager

if TYPE_CHECKING:
    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk.permission_handler import PermissionHandler
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.application.services.intent.detection_service import (
        IntentDetectionService,
    )
    from pilot_space.application.services.memory.memory_save_service import (
        MemorySaveService,
    )
    from pilot_space.application.services.memory.memory_search_service import (
        MemorySearchService,
    )


logger = get_logger(__name__)


@dataclass
class ChatInput:
    """Input for PilotSpace conversational agent."""

    message: str
    session_id: UUID | None = None
    resume_session_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    workspace_id: UUID | None = None


@dataclass
class ChatOutput:
    """Output from PilotSpace conversational agent."""

    response: str
    session_id: UUID
    tasks: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PilotSpaceAgent(StreamingSDKBaseAgent[ChatInput, ChatOutput]):
    """Main orchestrator agent — routes to skills, subagents, or direct responses."""

    AGENT_NAME = "pilotspace_agent"
    DEFAULT_MODEL_TIER: ClassVar[ModelTier] = ModelTier.SONNET

    SYSTEM_PROMPT_BASE: ClassVar[str] = PILOTSPACE_SYSTEM_PROMPT_BASE

    SUBAGENT_MAP: ClassVar[dict[str, str]] = {
        "pr-review": "PRReviewSubagent",
        # ai-context: now handled via ai-context skill (DD-086), no longer a subagent
        "doc-gen": "DocGeneratorSubagent",
    }

    def __init__(
        self,
        tool_registry: ToolRegistry,
        provider_selector: ProviderSelector,
        cost_tracker: CostTracker,
        resilient_executor: ResilientExecutor,
        permission_handler: PermissionHandler,
        session_handler: SessionHandler | None,
        space_manager: SpaceManager | None = None,
        subagents: dict[str, Any] | None = None,
        key_storage: SecureKeyStorage | None = None,
        intent_detection_service: IntentDetectionService | None = None,
        memory_search_service: MemorySearchService | None = None,
        memory_save_service: MemorySaveService | None = None,
    ) -> None:
        super().__init__(
            provider_selector=provider_selector,
            cost_tracker=cost_tracker,
            resilient_executor=resilient_executor,
        )
        self._permission_handler = permission_handler
        self._session_handler = session_handler
        self._space_manager = space_manager
        self._subagents = subagents or {}
        self._key_storage = key_storage
        self._intent_detection_service = intent_detection_service
        self._memory_search_service = memory_search_service
        self._memory_save_service = memory_save_service
        self._message_id_holder: dict[str, str | None] = {"_current_message_id": None}
        self._active_clients: dict[str, ClaudeSDKClient] = {}

    def _build_subagent_definitions(self) -> dict[str, AgentDefinition]:
        return build_subagent_definitions()

    async def _get_api_key(self, workspace_id: UUID | None) -> str:
        if workspace_id and self._key_storage:
            try:
                key = await self._key_storage.get_api_key(workspace_id, "anthropic")
                if key:
                    return key
            except Exception as e:
                logger.warning(
                    "Vault lookup failed for workspace %s: %s. Falling back to env var",
                    workspace_id,
                    str(e),
                    exc_info=True,
                )

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "Anthropic API key not found. Configure in workspace settings or set ANTHROPIC_API_KEY."
            raise ValueError(msg)
        return api_key

    async def interrupt_session(self, session_id: str) -> bool:
        client = self._active_clients.get(session_id)
        if not client:
            logger.debug("[SDK/Interrupt] No active client for session %s", session_id)
            return False

        try:
            await asyncio.wait_for(client.interrupt(), timeout=3.0)
            logger.info("[SDK/Interrupt] Interrupted session %s", session_id)
            return True
        except (TimeoutError, Exception) as e:
            logger.warning(
                "[SDK/Interrupt] Failed to interrupt session %s: %s",
                session_id,
                e,
            )
            return False

    async def submit_tool_result(
        self,
        session_id: str,
        tool_call_id: str,
        result: str,
    ) -> None:
        client = self._active_clients.get(session_id)
        if not client:
            raise ValueError(f"No active client for session {session_id}")

        answer_msg = f"[Answer to question {tool_call_id}]: {result}"
        await client.query(answer_msg, session_id=session_id)
        logger.info("[SDK/Answer] tool_call=%s session=%s", tool_call_id, session_id)

    @staticmethod
    def confirm_intent_event(
        session_id: str,
        *,
        intent_id: str | None = None,
        action: str = "confirmed",
    ) -> bool:
        """Signal the intent pipeline for session_id (T-018)."""
        return ConfirmationBus.signal(
            session_id,
            intent_id=intent_id,
            action=action,
        )

    async def _detect_and_emit_intents(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> list[str]:
        """Run intent detection and return SSE strings (T-016/T-017).

        Delegates to run_intent_pipeline_step; no-ops if service not injected.
        """
        return await run_intent_pipeline_step(
            detection_service=self._intent_detection_service,
            message=input_data.message,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            session_id=input_data.session_id,
        )

    async def _save_session_messages(
        self,
        input_data: ChatInput,
        content_blocks: dict[str, dict[str, Any]],
    ) -> None:
        """Persist user + assistant messages to session store (T-016)."""
        await save_session_messages(
            session_handler=self._session_handler,
            session_id=input_data.session_id,
            message=input_data.message,
            content_blocks=content_blocks,
        )

    def transform_sdk_message(
        self,
        message: Message,
        context: AgentContext,
        delta_buffer: DeltaBuffer | None = None,
        session_id: str | None = None,
    ) -> str | None:
        return transform_sdk_message_helper(
            message,
            self._message_id_holder,
            delta_buffer,
            app_session_id=session_id,
            user_id=context.user_id,
        )

    async def stream(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        try:
            api_key = await self._get_api_key(context.workspace_id)
            subagent_definitions = self._build_subagent_definitions()
            session_id_str = str(input_data.session_id) if input_data.session_id else None

            resume_id: str | None = None
            if input_data.resume_session_id and session_id_str:
                resume_id = session_id_str
                logger.info("Resuming SDK session: %s", resume_id)

            if not (self._space_manager and context.workspace_id and context.user_id):
                raise ValueError(  # noqa: TRY301
                    "SpaceManager, workspace_id, and user_id are required. "
                    "Legacy mode has been removed."
                )
            async for chunk in self._stream_with_space(
                input_data=input_data,
                context=context,
                api_key=api_key,
                subagent_definitions=subagent_definitions,
                session_id_str=session_id_str,
                resume_id=resume_id,
            ):
                yield chunk

        except Exception as e:
            err = {"errorCode": "sdk_error", "message": str(e), "retryable": False}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"

    async def _stream_with_space(
        self,
        input_data: ChatInput,
        context: AgentContext,
        api_key: str,
        subagent_definitions: dict[str, AgentDefinition],
        session_id_str: str | None,
        resume_id: str | None = None,
    ) -> AsyncIterator[str]:
        assert self._space_manager is not None
        assert context.workspace_id is not None
        assert context.user_id is not None

        space = self._space_manager.get_space(context.workspace_id, context.user_id)

        async with space.session() as space_context:
            tool_event_queue: asyncio.Queue[str] = asyncio.Queue()

            file_hook_executor = None
            if space_context.hooks_file.exists():
                from pilot_space.ai.sdk.file_hooks import FileBasedHookExecutor

                file_hook_executor = FileBasedHookExecutor(
                    space_context.hooks_file,
                    cwd=space_context.path,
                )
                logger.debug(f"[SDK/Space] Loaded hooks from {space_context.hooks_file}")

            from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

            hook_executor = PermissionAwareHookExecutor(
                permission_handler=self._permission_handler,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                file_hook_executor=file_hook_executor,
                event_queue=tool_event_queue,
            )

            from pilot_space.ai.tools.mcp_server import ToolContext
            from pilot_space.infrastructure.database import get_db_session

            db_session_cm = get_db_session()
            db_session = await db_session_cm.__aenter__()

            client: ClaudeSDKClient | None = None
            query_session_id = session_id_str or "default"
            stream_completed = False
            content_blocks: dict[str, dict[str, Any]] = {}

            try:
                skill_count = await materialize_role_skills(
                    db_session=db_session,
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    skills_dir=space_context.skills_dir,
                )

                has_skills = skill_count > 0 or await asyncio.to_thread(
                    has_skill_files,
                    space_context.skills_dir,
                )

                from pilot_space.infrastructure.database.repositories.role_skill_repository import (
                    RoleSkillRepository,
                )

                _role_repo = RoleSkillRepository(db_session)
                _primary_role = await _role_repo.get_primary_by_user_workspace(
                    context.user_id,
                    context.workspace_id,
                )
                _role_type = _primary_role.role_type if _primary_role else None

                if input_data.user_id is None:
                    raise ValueError("user_id is required for AI interactions")

                tool_context = ToolContext(
                    db_session=db_session,
                    workspace_id=str(context.workspace_id),
                    user_id=str(context.user_id) if context.user_id else None,
                )

                mcp_servers, ref_map = build_mcp_servers(
                    tool_event_queue,
                    tool_context,
                    input_data,
                )

                from pilot_space.ai.sdk.output_schemas import get_skill_output_format

                skill_name = detect_skill_from_message(input_data.message)
                output_format = get_skill_output_format(skill_name) if skill_name else None
                effort = classify_effort(input_data.message)
                streaming_input = estimate_tokens(input_data) > 30_000

                sdk_config = configure_sdk_for_space(
                    space_context,
                    permission_mode="default",
                    model=self.DEFAULT_MODEL_TIER,
                    additional_tools=ALL_TOOL_NAMES,
                    additional_env={
                        "ANTHROPIC_API_KEY": api_key,
                    },
                    hook_executor=hook_executor,
                    include_partial_messages=True,
                    memory_enabled=True,
                    citations_enabled=True,
                    system_prompt_base=await build_dynamic_system_prompt(
                        self.SYSTEM_PROMPT_BASE,
                        role_type=_role_type,
                        workspace_name=input_data.context.get("workspace_name"),
                        project_names=input_data.context.get("project_names"),
                    ),
                    output_format=output_format,
                    enable_file_checkpointing=True,
                    effort=effort,
                    streaming_input_mode=streaming_input,
                    skills_available=has_skills,
                )

                sdk_params = sdk_config.to_sdk_params()
                sdk_env = sdk_params.get("env", {})
                if "PATH" not in sdk_env:
                    sdk_env["PATH"] = os.environ.get("PATH", "")

                from pilot_space.ai.sdk.question_adapter import create_can_use_tool_callback

                can_use_tool_cb = create_can_use_tool_callback(tool_event_queue, context.user_id)

                sdk_options = ClaudeAgentOptions(
                    model=sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id),
                    cwd=sdk_params.get("cwd"),
                    setting_sources=sdk_params.get("setting_sources", ["project"]),
                    allowed_tools=sdk_params.get("allowed_tools", []),
                    mcp_servers=mcp_servers,
                    sandbox=sdk_params.get("sandbox"),
                    permission_mode=sdk_params.get("permission_mode", "default"),
                    env=sdk_env,
                    hooks=sdk_params.get("hooks"),
                    agents=subagent_definitions,
                    resume=resume_id,
                    continue_conversation=resume_id is not None,
                    include_partial_messages=sdk_params.get(
                        "include_partial_messages",
                        True,
                    ),
                    system_prompt=sdk_config.system_prompt_base,
                    max_thinking_tokens=sdk_config.max_thinking_tokens,
                    max_budget_usd=sdk_config.max_budget_usd,
                    max_turns=sdk_config.max_turns,
                    fallback_model=sdk_config.fallback_model,
                    output_format=sdk_config.output_format,
                    enable_file_checkpointing=sdk_config.enable_file_checkpointing,
                    can_use_tool=can_use_tool_cb,
                )

                set_workspace_context(context.workspace_id, context.user_id)
                logger.info(
                    "[SDK/Space] Config: cwd=%s, env_keys=%s, claude_bin=%s, "
                    "thinking_tokens=%s, system_prompt=%s, budget=%.2f",
                    sdk_params.get("cwd"),
                    list(sdk_env.keys()),
                    shutil.which("claude"),
                    sdk_config.max_thinking_tokens,
                    bool(sdk_config.system_prompt_base),
                    sdk_config.max_budget_usd or 0,
                )

                client = ClaudeSDKClient(sdk_options)

                delta_buffer = DeltaBuffer()

                await client.connect()

                logger.info(
                    "[SDK/Space] Client connected (session=%s, resume=%s)",
                    query_session_id,
                    resume_id,
                )

                self._active_clients[query_session_id] = client

                # T-048: recall memory context and inject into system prompt
                memory_entries = await recall_workspace_context(
                    workspace_id=context.workspace_id,
                    query=input_data.message,
                    memory_search_service=self._memory_search_service,
                )
                memory_prefix = build_memory_context_prefix(memory_entries)
                if memory_prefix:
                    existing = sdk_config.system_prompt_base or ""
                    sdk_config.system_prompt_base = memory_prefix + existing

                # T-016/T-017: detect intents
                intent_events = await self._detect_and_emit_intents(input_data, context)

                enriched_message = build_contextual_message(
                    input_data,
                    block_ref_map=ref_map,
                )
                await client.query(enriched_message, session_id=query_session_id)

                # Yield intent_detected events after query is dispatched
                for intent_sse in intent_events:
                    yield intent_sse
                    capture_content_from_sse(intent_sse, content_blocks)

                sdk_event_count = 0
                transformed_count = 0
                tool_event_count = 0
                stream_start = time.monotonic()
                ttft: float | None = None  # time-to-first-token

                try:
                    async for source, item in merge_sdk_and_queue(
                        client.receive_response(),
                        tool_event_queue,
                    ):
                        if source == "queue":
                            yield item
                            capture_content_from_sse(item, content_blocks)
                            tool_event_count += 1
                            continue

                        # source == "sdk"
                        sdk_event_count += 1
                        sse_event = self.transform_sdk_message(
                            item,
                            context,
                            delta_buffer,
                            session_id=session_id_str,
                        )
                        if sse_event:
                            if ttft is None:
                                ttft = time.monotonic() - stream_start
                                logger.info(
                                    "stream_ttft",
                                    ttft_ms=round(ttft * 1000, 1),
                                    session_id=session_id_str,
                                )
                            transformed_count += 1
                            yield sse_event
                            capture_content_from_sse(sse_event, content_blocks)

                        if delta_buffer.should_flush():
                            flush_event = delta_buffer.flush()
                            if flush_event:
                                transformed_count += 1
                                yield flush_event
                                capture_content_from_sse(flush_event, content_blocks)
                except Exception as stream_err:
                    partial_flush = delta_buffer.flush()
                    if partial_flush:
                        yield partial_flush
                    duration_ms = round((time.monotonic() - stream_start) * 1000, 1)
                    logger.error(
                        "stream_error",
                        session_id=query_session_id,
                        error=str(stream_err),
                        sdk_events_before_error=sdk_event_count,
                        duration_ms=duration_ms,
                        exc_info=True,
                    )
                    err = {
                        "errorCode": "stream_error",
                        "message": str(stream_err),
                        "retryable": False,
                    }
                    yield f"event: error\ndata: {json.dumps(err)}\n\n"
                else:
                    final_flush = delta_buffer.flush()
                    if final_flush:
                        transformed_count += 1
                        yield final_flush
                        capture_content_from_sse(final_flush, content_blocks)

                    try:
                        while True:
                            drain_item = tool_event_queue.get_nowait()
                            yield drain_item
                            capture_content_from_sse(drain_item, content_blocks)
                            tool_event_count += 1
                    except asyncio.QueueEmpty:
                        pass

                    stream_completed = True
                    duration_ms = round((time.monotonic() - stream_start) * 1000, 1)
                    logger.info(
                        "stream_completed",
                        sdk_events=sdk_event_count,
                        transformed=transformed_count,
                        tool_events=tool_event_count,
                        duration_ms=duration_ms,
                        ttft_ms=round(ttft * 1000, 1) if ttft else None,
                        session_id=session_id_str,
                    )

            finally:
                self._active_clients.pop(query_session_id, None)

                if client is not None:
                    if not stream_completed:
                        try:
                            await asyncio.wait_for(client.interrupt(), timeout=2.0)
                            logger.info(
                                "[SDK/Space] Sent interrupt to Claude process (session=%s)",
                                query_session_id,
                            )
                        except (TimeoutError, Exception) as e:
                            logger.debug("[SDK/Space] Interrupt during cleanup failed: %s", e)

                    if stream_completed:
                        await self._save_session_messages(input_data, content_blocks)

                        # T-050: save conversation outcome to workspace memory
                        if content_blocks:
                            outcome_summary = " ".join(
                                block.get("text", "")[:200]
                                for block in content_blocks.values()
                                if block.get("text")
                            )[:500]
                            if outcome_summary and context.workspace_id:
                                await save_skill_outcome_to_memory(
                                    memory_save_service=self._memory_save_service,
                                    workspace_id=context.workspace_id,
                                    content=outcome_summary,
                                )

                    await client.disconnect()

                clear_context()
                try:
                    await db_session_cm.__aexit__(None, None, None)
                except Exception as db_err:
                    logger.warning("[SDK/Space] DB session cleanup error: %s", db_err)

    async def create_client(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> tuple[ClaudeSDKClient, str]:
        """Create unconnected ClaudeSDKClient. Caller manages connect()/disconnect()."""
        api_key = await self._get_api_key(context.workspace_id)
        subagent_definitions = self._build_subagent_definitions()

        session_id_str = "default"
        if input_data.session_id and self._session_handler:
            existing = await self._session_handler.get_session(input_data.session_id)
            if existing:
                session_id_str = str(existing.session_id)

        if not (self._space_manager and context.workspace_id and context.user_id):
            msg = (
                "SpaceManager, workspace_id, and user_id are required. "
                "Legacy mode has been removed."
            )
            raise ValueError(msg)

        space = self._space_manager.get_space(context.workspace_id, context.user_id)
        async with space.session() as space_context:
            sdk_config = configure_sdk_for_space(
                space_context,
                permission_mode="default",
                additional_env={"ANTHROPIC_API_KEY": api_key},
            )
            sdk_params = sdk_config.to_sdk_params()

            sdk_env = sdk_params.get("env", {})
            if "PATH" not in sdk_env:
                sdk_env["PATH"] = os.environ.get("PATH", "")

            sdk_options = ClaudeAgentOptions(
                model=sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id),
                cwd=sdk_params.get("cwd"),
                setting_sources=sdk_params.get("setting_sources", ["project"]),
                allowed_tools=sdk_params.get("allowed_tools", []),
                sandbox=sdk_params.get("sandbox"),
                permission_mode=sdk_params.get("permission_mode", "default"),
                env=sdk_env,
                hooks=sdk_params.get("hooks"),
                agents=subagent_definitions,
                resume=session_id_str if session_id_str != "default" else None,
                system_prompt=sdk_config.system_prompt_base,
                max_thinking_tokens=sdk_config.max_thinking_tokens,
                max_budget_usd=sdk_config.max_budget_usd,
                max_turns=sdk_config.max_turns,
                fallback_model=sdk_config.fallback_model,
                output_format=sdk_config.output_format,
                enable_file_checkpointing=sdk_config.enable_file_checkpointing,
            )

            return ClaudeSDKClient(sdk_options), session_id_str

    async def execute(self, input_data: ChatInput, context: AgentContext) -> ChatOutput:
        """Non-streaming execution that collects all chunks into ChatOutput."""
        chunks = [
            chunk[6:] if chunk.startswith("data: ") else chunk
            async for chunk in self.stream(input_data, context)
        ]
        sid = (
            input_data.session_id
            or context.operation_id
            or UUID("00000000-0000-0000-0000-000000000000")
        )
        return ChatOutput(
            response="".join(chunks),
            session_id=sid,
            tasks=[],
            metadata={"agent": self.AGENT_NAME, "model": self.DEFAULT_MODEL_TIER.model_id},
        )
