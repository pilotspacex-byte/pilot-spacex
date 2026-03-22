"""PilotSpace Agent - Centralized orchestrator."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    Message,
    ResultMessage,
)

from pilot_space.ai.agents.agent_base import AgentContext, StreamingSDKBaseAgent
from pilot_space.ai.agents.pilotspace_agent_helpers import (
    ALL_TOOL_NAMES,
    build_contextual_message,
    build_subagent_definitions,
    has_skill_files,
    transform_sdk_message as transform_sdk_message_helper,
)
from pilot_space.ai.agents.pilotspace_intent_pipeline import (
    ConfirmationBus,
    recall_graph_context,
    run_intent_pipeline_step,
)
from pilot_space.ai.agents.pilotspace_stream_utils import (
    _load_remote_mcp_servers,  # type: ignore[reportPrivateUsage]
    build_graph_search_service_for_session,
    build_graph_write_service_for_session,
    build_mcp_servers,
    capture_content_from_sse,
    classify_effort,
    detect_skill_from_message,
    estimate_tokens,
    get_workspace_embedding_key,
    merge_sdk_and_queue,
    save_session_messages,
)
from pilot_space.ai.agents.role_skill_materializer import materialize_role_skills
from pilot_space.ai.agents.sse_delta_buffer import DeltaBuffer
from pilot_space.ai.context import clear_context, set_workspace_context
from pilot_space.ai.prompt import PromptLayerConfig, assemble_system_prompt
from pilot_space.ai.sdk.sandbox_config import ModelTier, configure_sdk_for_space
from pilot_space.infrastructure.logging import get_logger
from pilot_space.spaces.manager import SpaceManager

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pilot_space.ai.infrastructure.cost_tracker import CostTracker
    from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
    from pilot_space.ai.infrastructure.resilience import ResilientExecutor
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap
    from pilot_space.ai.providers.provider_selector import ProviderSelector
    from pilot_space.ai.sdk.permission_handler import PermissionHandler
    from pilot_space.ai.sdk.session_handler import SessionHandler
    from pilot_space.ai.tools.mcp_server import ToolRegistry
    from pilot_space.application.services.intent.detection_service import IntentDetectionService
    from pilot_space.application.services.memory.memory_save_service import MemorySaveService
    from pilot_space.application.services.memory.memory_search_service import MemorySearchService
    from pilot_space.infrastructure.queue.supabase_queue import SupabaseQueueClient
    from pilot_space.spaces.base import SpaceContext

logger = get_logger(__name__)


async def _background_graph_extraction(
    graph_queue_client: Any,
    workspace_id: UUID,
    user_id: UUID | None,
    messages: list[dict[str, str]],
    issue_id: UUID | None = None,
    anthropic_api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> None:
    """Run graph extraction in a background task with its own DB session.

    Separates the slow LLM call from the write phase so the DB session is
    held only during the actual persistence step, not during the ~20-25s
    LLM round-trip.

    Phase 1 (no DB session): LLM extraction — identifies decisions, patterns,
      and user preferences from the conversation.
    Phase 2 (scoped DB session with RLS): persistence — writes extracted nodes
      and edges to the RLS-protected graph tables.
    """
    if not messages:
        return
    if not anthropic_api_key and not base_url:
        return

    try:
        from pilot_space.application.services.memory.graph_extraction_service import (
            ConversationExtractionPayload,
            GraphExtractionService,
        )
        from pilot_space.application.services.memory.graph_write_service import GraphWritePayload
        from pilot_space.infrastructure.database import get_db_session
        from pilot_space.infrastructure.database.rls import set_rls_context

        # Phase 1: LLM call — outside DB session to avoid holding a connection
        # for the full ~20-25s extraction round-trip.
        extraction_svc = GraphExtractionService()
        result = await extraction_svc.execute(
            ConversationExtractionPayload(
                messages=messages,
                workspace_id=workspace_id,
                user_id=user_id,
                issue_id=issue_id,
                api_key=anthropic_api_key or "ollama",
                base_url=base_url,
                model_name=model_name,
            )
        )

        if not result.nodes:
            logger.debug(
                "[SDK/BackgroundGraph] No meaningful nodes extracted workspace=%s",
                workspace_id,
            )
            return

        # Phase 2: Write phase — open session only now that we have data to persist.
        # set_rls_context is required: graph tables are RLS-protected and inserts
        # will be denied without the app.current_user_id session variable.
        async with get_db_session() as bg_session:
            if user_id is not None:
                await set_rls_context(bg_session, user_id, workspace_id)
            graph_write_svc = build_graph_write_service_for_session(bg_session, graph_queue_client)
            await graph_write_svc.execute(
                GraphWritePayload(
                    workspace_id=workspace_id,
                    nodes=result.nodes,
                    edges=result.edges,
                    user_id=user_id,
                    issue_id=issue_id,
                )
            )
            logger.info(
                "[SDK/BackgroundGraph] Extracted %d nodes, %d edges to knowledge graph workspace=%s",
                len(result.nodes),
                len(result.edges),
                workspace_id,
            )
    except Exception:
        logger.warning(
            "[SDK/BackgroundGraph] Graph extraction task failed (non-fatal)",
            exc_info=True,
        )


@dataclass
class ChatInput:
    """Input for PilotSpace conversational agent."""

    message: str
    session_id: UUID | None = None
    resume_session_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    workspace_id: UUID | None = None
    resolved_model: Any | None = None  # ResolvedModelConfig when model_override set (AIPR-04)


@dataclass
class ChatOutput:
    """Output from PilotSpace conversational agent."""

    response: str
    session_id: UUID
    tasks: list[dict[str, Any]] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _ProviderConfig:
    """Resolved LLM provider configuration for the workspace."""

    api_key: str
    base_url: str | None = None
    model_name: str | None = None
    provider: str = "anthropic"


@dataclass(frozen=True, slots=True)
class _StreamConfig:
    sdk_options: ClaudeAgentOptions
    ref_map: BlockRefMap | None


class PilotSpaceAgent(StreamingSDKBaseAgent[ChatInput, ChatOutput]):
    """Main orchestrator agent — routes to skills, subagents, or direct responses."""

    AGENT_NAME = "pilotspace_agent"
    DEFAULT_MODEL_TIER: ClassVar[ModelTier] = ModelTier.SONNET

    _DEFAULT_SESSION_ID: ClassVar[str] = "default"

    SUBAGENT_MAP: ClassVar[dict[str, str]] = {
        "pr-review": "PRReviewSubagent",
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
        graph_queue_client: SupabaseQueueClient | None = None,
        session_factory: Any | None = None,
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
        self._graph_queue_client = graph_queue_client
        self._session_factory = session_factory
        self._message_id_holder: dict[str, str | None] = {"_current_message_id": None}
        self._active_clients: dict[str, ClaudeSDKClient] = {}
        # Strong references to fire-and-forget background tasks.
        # asyncio only keeps weak references to tasks; without this set a task
        # can be garbage-collected mid-execution before it completes.
        self._background_tasks: set[asyncio.Task[None]] = set()

    def _build_subagent_definitions(self) -> dict[str, AgentDefinition]:
        return build_subagent_definitions()

    async def _get_provider_config(self, workspace_id: UUID | None) -> _ProviderConfig:
        """Resolve LLM provider config from workspace settings (AIGOV-05 BYOK).

        Reads workspace.settings.default_llm_provider, then looks up that
        provider's api_key, base_url, and model_name from workspace_api_keys.
        Falls back to app-level ANTHROPIC_API_KEY env var.
        """
        # AIPR-04: explicit model override from frontend takes priority
        if getattr(self, "_resolved_model", None) is not None:
            return _ProviderConfig(
                api_key=self._resolved_model.api_key,  # type: ignore[union-attr]
                base_url=getattr(self._resolved_model, "base_url", None),
                model_name=getattr(self._resolved_model, "model", None),
            )

        from pilot_space.ai.exceptions import AINotConfiguredError

        if workspace_id is not None:
            try:
                from pilot_space.ai.infrastructure.key_storage import SecureKeyStorage
                from pilot_space.config import get_settings
                from pilot_space.dependencies.auth import get_current_session

                ks = SecureKeyStorage(
                    db=get_current_session(),
                    master_secret=get_settings().encryption_key.get_secret_value(),
                )
            except RuntimeError:
                logger.debug("[SDK/ProviderConfig] No request session, using singleton key_storage")
                ks = self._key_storage

            if ks:
                config = await self._resolve_workspace_provider(ks, workspace_id)
                if config is not None:
                    logger.info(
                        "[SDK/ProviderConfig] Resolved: provider=%s, model=%s, has_base_url=%s",
                        config.provider,
                        config.model_name or "default",
                        bool(config.base_url),
                    )
                    return config
                logger.warning(
                    "[SDK/ProviderConfig] _resolve_workspace_provider returned None for workspace=%s",
                    workspace_id,
                )

            raise AINotConfiguredError(workspace_id=workspace_id)

        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            return _ProviderConfig(api_key=api_key)
        raise AINotConfiguredError(workspace_id=None)

    async def _resolve_workspace_provider(
        self,
        ks: Any,
        workspace_id: UUID,
    ) -> _ProviderConfig | None:
        """Resolve provider from workspace settings → workspace_api_keys."""
        from sqlalchemy import select as sa_select

        from pilot_space.infrastructure.database.models.workspace import Workspace

        # Determine default LLM provider from workspace settings.
        # Try request-scoped session first; fall back to key_storage's own session
        # so provider resolution works outside request contexts (e.g. background tasks).
        db = getattr(ks, "db", None)
        if db is None:
            try:
                from pilot_space.dependencies.auth import get_current_session

                db = get_current_session()
            except RuntimeError:
                logger.debug("[SDK/ResolveProvider] No DB session available")
                return None

        stmt = sa_select(Workspace.settings).where(Workspace.id == workspace_id)
        result = await db.execute(stmt)
        ws_settings = result.scalar_one_or_none() or {}
        default_provider = ws_settings.get("default_llm_provider", "anthropic")
        logger.debug(
            "[SDK/ResolveProvider] workspace=%s default_llm_provider=%s",
            workspace_id,
            default_provider,
        )

        # Try the default provider first
        key_info = await ks.get_key_info(workspace_id, default_provider, "llm")
        if key_info is not None:
            api_key = await ks.get_api_key(workspace_id, default_provider, "llm")
            logger.debug(
                "[SDK/ResolveProvider] Found key for %s: has_base_url=%s, model_name=%s, has_key=%s",
                default_provider,
                bool(key_info.base_url),
                key_info.model_name,
                bool(api_key),
            )
            return _ProviderConfig(
                api_key=api_key or "no-key-required",  # Ollama doesn't need a real key
                base_url=key_info.base_url,
                model_name=key_info.model_name,
                provider=default_provider,
            )

        # Fall back to any configured LLM provider
        all_keys = await ks.get_all_key_infos(workspace_id)
        logger.debug(
            "[SDK/ResolveProvider] Default provider %s has no key, checking %d total keys",
            default_provider,
            len(all_keys),
        )
        for ki in all_keys:
            if ki.service_type == "llm":
                api_key = await ks.get_api_key(workspace_id, ki.provider, "llm")
                if api_key or ki.base_url:  # Ollama has base_url but no key
                    return _ProviderConfig(
                        api_key=api_key or "no-key-required",
                        base_url=ki.base_url,
                        model_name=ki.model_name,
                        provider=ki.provider,
                    )

        logger.warning("[SDK/ResolveProvider] No LLM key found for workspace=%s", workspace_id)
        return None

    async def interrupt_session(self, session_id: str) -> bool:
        client = self._active_clients.get(session_id)
        if not client:
            logger.debug("[SDK/Interrupt] No active client for session %s", session_id)
            return False

        try:
            await asyncio.wait_for(client.interrupt(), timeout=3.0)
            logger.info("[SDK/Interrupt] Interrupted session %s", session_id)
            return True
        except Exception as e:  # Intentional catch-all: corrupt client must not crash caller
            logger.warning("[SDK/Interrupt] Failed to interrupt session %s: %s", session_id, e)
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
        try:
            await asyncio.wait_for(
                client.query(answer_msg, session_id=session_id),
                timeout=10.0,
            )
        except TimeoutError as exc:
            logger.warning(
                "[SDK/Answer] Timed out submitting tool result: tool_call=%s session=%s",
                tool_call_id,
                session_id,
            )
            raise TimeoutError("Tool result submission timed out") from exc
        logger.info("[SDK/Answer] tool_call=%s session=%s", tool_call_id, session_id)

    @staticmethod
    def confirm_intent_event(
        session_id: str,
        *,
        intent_id: str | None = None,
        action: str = "confirmed",
    ) -> bool:
        """Signal the intent pipeline for session_id (T-018)."""
        return ConfirmationBus.signal(session_id, intent_id=intent_id, action=action)

    async def _detect_and_emit_intents(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> list[str]:
        """Run intent detection and return SSE strings (T-016/T-017). No-ops if service not injected."""
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

    async def _track_stream_cost(
        self,
        usage: dict[str, Any] | None,
        content_blocks: dict[str, dict[str, Any]],
        context: AgentContext,
        provider_config: _ProviderConfig,
    ) -> None:
        """Record SDK stream usage to cost DB. Non-fatal."""
        usage = getattr(self, "_last_stream_usage", None)
        if usage is None:
            return

        input_tokens = int(usage.get("inputTokens") or 0)
        output_tokens = int(usage.get("outputTokens") or 0)
        if not (input_tokens or output_tokens):
            return

        model = provider_config.model_name or self.DEFAULT_MODEL
        provider = provider_config.provider

        try:
            await self._cost_tracker.track(
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                agent_name=self.AGENT_NAME,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                operation_type="chat",
            )
        except Exception:
            logger.warning(
                "pilotspace_agent_cost_tracking_failed",
                workspace_id=str(context.workspace_id),
            )
        finally:
            self._last_stream_usage = None

    def transform_sdk_message(
        self,
        message: Message,
        context: AgentContext,
        delta_buffer: DeltaBuffer | None = None,
        session_id: str | None = None,
        stream_usage_holder: dict[str, Any] | None = None,
    ) -> str | None:
        # Capture usage from ResultMessage for cost tracking
        if isinstance(message, ResultMessage):
            from pilot_space.ai.infrastructure.cost_tracker import extract_response_usage

            input_tokens, output_tokens = extract_response_usage(message)
            if (input_tokens or output_tokens) and stream_usage_holder is not None:
                stream_usage_holder.clear()
                stream_usage_holder.update(
                    {
                        "inputTokens": input_tokens,
                        "outputTokens": output_tokens,
                        "costUsd": getattr(message, "total_cost_usd", None),
                    }
                )
            if input_tokens or output_tokens:
                self._last_stream_usage = {
                    "inputTokens": input_tokens,
                    "outputTokens": output_tokens,
                    "costUsd": getattr(message, "total_cost_usd", None),
                }

        return transform_sdk_message_helper(
            message,
            self._message_id_holder,
            delta_buffer,
            app_session_id=session_id,
            user_id=context.user_id,
        )

    async def _build_stream_config(
        self,
        db_session: AsyncSession,
        space_context: SpaceContext,
        input_data: ChatInput,
        context: AgentContext,
        hook_executor: Any,
        tool_event_queue: asyncio.Queue[str],
        subagent_definitions: dict[str, AgentDefinition],
        provider_config: _ProviderConfig,
        resume_id: str | None,
    ) -> _StreamConfig:
        """Build SDK options and MCP config for a streaming session."""
        from pilot_space.ai.sdk.output_schemas import get_skill_output_format
        from pilot_space.ai.sdk.question_adapter import create_can_use_tool_callback
        from pilot_space.ai.tools.mcp_server import ToolContext
        from pilot_space.infrastructure.database.repositories.role_skill_repository import (
            RoleSkillRepository,
        )
        from pilot_space.infrastructure.database.repositories.user_skill_repository import (
            UserSkillRepository,
        )
        from pilot_space.infrastructure.database.repositories.workspace_repository import (
            WorkspaceRepository,
        )
        from pilot_space.infrastructure.database.rls import set_rls_context

        await set_rls_context(db_session, context.user_id, context.workspace_id)

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

        # Load user skills for prompt-level awareness (separate from disk materialization)
        _user_skills_for_prompt: list[dict[str, str]] = []
        try:
            _active_skills = await UserSkillRepository(db_session).get_active_by_user_workspace(
                context.user_id, context.workspace_id
            )
            for _s in _active_skills:
                name = _s.skill_name or (_s.template.name if _s.template else str(_s.id)[:8])
                desc = (
                    f"Personalized {_s.template.name} skill"
                    if _s.template
                    else (_s.experience_description or "")[:120]
                )
                _user_skills_for_prompt.append({"name": name, "description": desc})
        except Exception:
            logger.warning("Failed to load user skills for prompt", exc_info=True)

        _role_repo = RoleSkillRepository(db_session)
        _primary_role = await _role_repo.get_primary_by_user_workspace(
            context.user_id,
            context.workspace_id,
        )
        _role_type = _primary_role.role_type if _primary_role else None

        if input_data.user_id is None:
            raise ValueError("user_id is required for AI interactions")

        # Fetch workspace membership role for approval policy checks
        _workspace_repo = WorkspaceRepository(db_session)
        _ws_member_role = await _workspace_repo.get_member_role(
            context.workspace_id, context.user_id
        )

        # Load workspace feature toggles for skill/MCP filtering.
        # Normalize to a full dict by merging schema defaults with any stored
        # overrides so that missing keys never silently disable features.
        from pilot_space.api.v1.schemas.workspace import WorkspaceFeatureToggles

        _toggle_defaults: dict[str, bool] = WorkspaceFeatureToggles().model_dump()
        _workspace_obj = await _workspace_repo.get_by_id(context.workspace_id)
        _raw_toggles = (
            (_workspace_obj.settings or {}).get("feature_toggles") if _workspace_obj else None
        )
        # Validate: stored value must be a mapping; non-boolean values are coerced/dropped.
        _stored_toggles: dict[str, bool] = (
            {k: bool(v) for k, v in _raw_toggles.items() if isinstance(v, bool)}
            if isinstance(_raw_toggles, dict)
            else {}
        )
        _feature_toggles: dict[str, bool] = {**_toggle_defaults, **_stored_toggles}

        tool_context = ToolContext(
            db_session=db_session,
            workspace_id=str(context.workspace_id),
            user_id=str(context.user_id) if context.user_id else None,
            user_role=_ws_member_role,
        )

        # MCP-04: pre-fetch async before sync build_mcp_servers, then merge
        remote_servers = await _load_remote_mcp_servers(context.workspace_id, db_session)
        mcp_servers, ref_map = build_mcp_servers(
            tool_event_queue, tool_context, input_data, feature_toggles=_feature_toggles
        )
        mcp_servers.update(remote_servers)

        skill_name = detect_skill_from_message(input_data.message)
        output_format = get_skill_output_format(skill_name) if skill_name else None
        effort = classify_effort(input_data.message)
        streaming_input = estimate_tokens(input_data) > 30_000

        _openai_key_for_recall = await get_workspace_embedding_key(db_session, context.workspace_id)
        graph_context = await recall_graph_context(
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            query=input_data.message,
            graph_search_service=build_graph_search_service_for_session(  # fresh per-req
                db_session, openai_api_key=_openai_key_for_recall
            ),
        )

        assembled = await assemble_system_prompt(
            PromptLayerConfig(
                role_type=_role_type,
                workspace_name=input_data.context.get("workspace_name"),
                project_names=input_data.context.get("project_names"),
                user_message=input_data.message,
                has_note_context="<note_context>" in input_data.message,
                graph_context=graph_context,
                user_skills=_user_skills_for_prompt,
                feature_toggles=_feature_toggles,
            )
        )

        # Build env with workspace provider's API key and base URL
        provider_env: dict[str, str] = {
            "ANTHROPIC_API_KEY": provider_config.api_key,
        }
        if provider_config.base_url:
            provider_env["ANTHROPIC_BASE_URL"] = provider_config.base_url
        logger.info(
            "[SDK/Space] Provider: %s, has_base_url=%s, model=%s",
            provider_config.provider,
            bool(provider_config.base_url),
            provider_config.model_name or "default",
        )

        sdk_config = configure_sdk_for_space(
            space_context,
            permission_mode="default",
            model=self.DEFAULT_MODEL_TIER,
            additional_tools=ALL_TOOL_NAMES,
            additional_env=provider_env,
            hook_executor=hook_executor,
            include_partial_messages=True,
            memory_enabled=True,
            citations_enabled=True,
            system_prompt_base=assembled.prompt,
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

        can_use_tool_cb = create_can_use_tool_callback(tool_event_queue, context.user_id)

        _r = getattr(self, "_resolved_model", None)  # AIPR-04 model override
        # Model priority: AIPR-04 override > workspace provider config > SDK default
        _model = (
            _r.model
            if _r
            else (
                provider_config.model_name
                or sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id)
            )
        )
        logger.info(
            "[SDK/Space] Model resolution: resolved=%s, provider_model=%s, sdk_default=%s, has_base_url=%s",
            _model,
            provider_config.model_name,
            sdk_params.get("model", self.DEFAULT_MODEL_TIER.model_id),
            bool(provider_config.base_url),
        )
        sdk_options = ClaudeAgentOptions(
            model=_model,
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
            include_partial_messages=sdk_params.get("include_partial_messages", True),
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
            "[SDK/Space] Config: cwd=%s, thinking_tokens=%s, system_prompt=%s, budget=%.2f",
            sdk_params.get("cwd"),
            sdk_config.max_thinking_tokens,
            bool(sdk_config.system_prompt_base),
            sdk_config.max_budget_usd or 0,
        )
        logger.debug("[SDK/Space] Detail: env_keys=%s", list(sdk_env.keys()))  # Safe

        return _StreamConfig(sdk_options=sdk_options, ref_map=ref_map)

    async def stream(
        self,
        input_data: ChatInput,
        context: AgentContext,
    ) -> AsyncIterator[str]:
        try:
            self._resolved_model = input_data.resolved_model  # AIPR-04
            provider_config = await self._get_provider_config(context.workspace_id)
            subagent_definitions = self._build_subagent_definitions()
            session_id_str = str(input_data.session_id) if input_data.session_id else None

            resume_id: str | None = None
            if input_data.resume_session_id and session_id_str:
                resume_id = session_id_str
                logger.info("Resuming SDK session: %s", resume_id)

            if not (self._space_manager and context.workspace_id and context.user_id):
                raise ValueError("SpaceManager, workspace_id, and user_id are required.")  # noqa: TRY301
            async for chunk in self._stream_with_space(
                input_data=input_data,
                context=context,
                provider_config=provider_config,
                subagent_definitions=subagent_definitions,
                session_id_str=session_id_str,
                resume_id=resume_id,
            ):
                yield chunk

        except Exception as e:
            logger.error("[SDK/Stream] Top-level error: %s: %s", type(e).__name__, e, exc_info=True)
            err = {"errorCode": "sdk_error", "message": str(e), "retryable": False}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"

    async def _stream_with_space(
        self,
        input_data: ChatInput,
        context: AgentContext,
        provider_config: _ProviderConfig,
        subagent_definitions: dict[str, AgentDefinition],
        session_id_str: str | None,
        resume_id: str | None = None,
    ) -> AsyncIterator[str]:
        if not (self._space_manager and context.workspace_id and context.user_id):
            raise ValueError("SpaceManager, workspace_id, and user_id are required for streaming")

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
                logger.debug("[SDK/Space] Loaded hooks from %s", space_context.hooks_file)

            from pilot_space.ai.sdk.hooks import PermissionAwareHookExecutor

            hook_executor = PermissionAwareHookExecutor(
                permission_handler=self._permission_handler,
                workspace_id=context.workspace_id,
                user_id=context.user_id,
                file_hook_executor=file_hook_executor,
                event_queue=tool_event_queue,
                session_factory=self._session_factory,
            )

            from pilot_space.infrastructure.database import get_db_session

            db_session_cm = get_db_session()
            db_session: AsyncSession | None = None

            client: ClaudeSDKClient | None = None
            query_session_id = session_id_str or self._DEFAULT_SESSION_ID
            stream_completed = False
            content_blocks: dict[str, dict[str, Any]] = {}
            _stream_error: BaseException | None = None

            try:
                db_session = await db_session_cm.__aenter__()

                config = await self._build_stream_config(
                    db_session=db_session,
                    space_context=space_context,
                    input_data=input_data,
                    context=context,
                    hook_executor=hook_executor,
                    tool_event_queue=tool_event_queue,
                    subagent_definitions=subagent_definitions,
                    provider_config=provider_config,
                    resume_id=resume_id,
                )
                sdk_options = config.sdk_options
                ref_map = config.ref_map

                client = ClaudeSDKClient(sdk_options)

                delta_buffer = DeltaBuffer()

                await client.connect()

                logger.info(
                    "[SDK/Space] Client connected (session=%s, resume=%s)",
                    query_session_id,
                    resume_id,
                )

                self._active_clients[query_session_id] = client

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
                stream_usage: dict[str, Any] = {}  # request-local usage

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
                            stream_usage_holder=stream_usage,
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
                    _stream_error = stream_err
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
                    yield f"event: error\ndata: {json.dumps({'errorCode': 'stream_error', 'message': str(stream_err), 'retryable': False})}\n\n"
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

                    # Track cost from SDK usage (extracted in message_stop SSE)
                    await self._track_stream_cost(
                        stream_usage or None,
                        content_blocks,
                        context,
                        provider_config,
                    )

            finally:
                self._active_clients.pop(query_session_id, None)
                if client is not None:
                    if not stream_completed:
                        with contextlib.suppress(Exception):
                            await asyncio.wait_for(client.interrupt(), timeout=2.0)
                    if stream_completed:
                        await self._save_session_messages(input_data, content_blocks)

                        # T-050: persist conversation outcome to knowledge graph
                        # Fire-and-forget: graph extraction makes an LLM call (~20-25s)
                        # that must NOT block SSE connection closure.
                        if content_blocks and context.workspace_id:
                            assistant_texts = [
                                block.get("text", "")
                                for block in content_blocks.values()
                                if block.get("text")
                            ]
                            if assistant_texts:
                                _ctx_issue = input_data.context.get("issue_id")
                                _issue_id_uuid: UUID | None = None
                                if _ctx_issue is not None:
                                    _issue_id_uuid = (
                                        _ctx_issue
                                        if isinstance(_ctx_issue, UUID)
                                        else UUID(str(_ctx_issue))
                                    )
                                _bg_task = asyncio.create_task(
                                    _background_graph_extraction(
                                        graph_queue_client=self._graph_queue_client,
                                        workspace_id=context.workspace_id,
                                        user_id=context.user_id,
                                        messages=[
                                            {"role": "user", "content": input_data.message},
                                            {"role": "assistant", "content": assistant_texts[-1]},
                                        ],
                                        issue_id=_issue_id_uuid,
                                        anthropic_api_key=provider_config.api_key,
                                        base_url=provider_config.base_url,
                                        model_name=provider_config.model_name,
                                    )
                                )
                                # Keep a strong reference so asyncio's weak-ref
                                # GC cannot discard the task mid-execution.
                                self._background_tasks.add(_bg_task)
                                _bg_task.add_done_callback(self._background_tasks.discard)

                    await client.disconnect()
                clear_context()
                # Propagate error info so db_session_cm rolls back on failure (D-1 fix).
                # Manual __aexit__ is necessary: caught stream errors (in _stream_error)
                # must trigger DB rollback even though they are not re-raised.
                if db_session is not None:
                    active_err = _stream_error or sys.exc_info()[1]
                    try:
                        if active_err is not None:
                            await db_session_cm.__aexit__(
                                type(active_err), active_err, active_err.__traceback__
                            )
                        else:
                            await db_session_cm.__aexit__(None, None, None)
                    except Exception as db_err:
                        logger.warning("[SDK/Space] DB session cleanup error: %s", db_err)

    async def execute(self, input_data: ChatInput, context: AgentContext) -> ChatOutput:
        """Non-streaming execution that collects all chunks into ChatOutput."""
        chunks = [
            chunk[6:] if chunk.startswith("data: ") else chunk
            async for chunk in self.stream(input_data, context)
        ]
        sid = input_data.session_id or context.operation_id or UUID(int=0)
        return ChatOutput(
            response="".join(chunks),
            session_id=sid,
            tasks=[],
            metadata={"agent": self.AGENT_NAME, "model": self.DEFAULT_MODEL_TIER.model_id},
        )
