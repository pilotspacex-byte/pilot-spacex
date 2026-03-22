"""Unit tests for PilotSpace stream utility functions.

Tests build_structured_content, capture_content_from_sse, helper functions
extracted from pilotspace_agent.py, and merge_sdk_and_queue concurrent merge.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from pilot_space.ai.agents.pilotspace_stream_utils import (
    build_structured_content,
    capture_content_from_sse,
    classify_effort,
    detect_skill_from_message,
    extract_question_data_from_blocks,
    extract_tool_calls_from_blocks,
    get_workspace_embedding_key,
    get_workspace_openai_key,
    merge_sdk_and_queue,
)


class TestBuildStructuredContent:
    """Test structured content building for session persistence."""

    def test_empty_blocks_returns_empty_string(self) -> None:
        """No content blocks produces empty string."""
        assert build_structured_content({}) == ""

    def test_text_only_returns_plain_string(self) -> None:
        """Text-only blocks return concatenated plain text."""
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello ", "index": 0},
            "text_1": {"type": "text", "text": "world", "index": 1},
        }
        result = build_structured_content(blocks)
        assert result == "Hello world"

    def test_thinking_with_signature_preserved(self) -> None:
        """Thinking blocks WITH signatures are included in output."""
        blocks: dict[str, dict[str, Any]] = {
            "thinking_0": {
                "type": "thinking",
                "thinking": "Let me analyze...",
                "signature": "EqoB_valid",
                "index": 0,
            },
            "text_1": {"type": "text", "text": "Here is my answer", "index": 1},
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        types = [b["type"] for b in result]
        assert "thinking" in types

    def test_thinking_without_signature_stripped(self) -> None:
        """Thinking blocks WITHOUT signatures are dropped to prevent API errors."""
        blocks: dict[str, dict[str, Any]] = {
            "thinking_0": {
                "type": "thinking",
                "thinking": "Incomplete thinking...",
                "index": 0,
            },
            "text_1": {"type": "text", "text": "Answer", "index": 1},
            "tool_use_abc": {
                "type": "tool_use",
                "id": "abc",
                "name": "skill",
                "input": {},
                "index": 2,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        types = [b["type"] for b in result]
        assert "thinking" not in types
        assert "text" in types
        assert "tool_use" in types

    def test_tool_use_and_result_preserved(self) -> None:
        """Tool use and result blocks are always preserved."""
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_t1": {
                "type": "tool_use",
                "id": "t1",
                "name": "extract_issues",
                "input": {},
                "index": 0,
            },
            "tool_result_t1": {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Success",
                "is_error": False,
                "index": 1,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_index_field_removed_from_output(self) -> None:
        """Internal index field is stripped from persisted blocks."""
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello", "index": 0},
            "tool_use_t1": {
                "type": "tool_use",
                "id": "t1",
                "name": "read",
                "input": {},
                "index": 1,
            },
        }
        result = build_structured_content(blocks)
        assert isinstance(result, list)
        for block in result:
            assert "index" not in block


class TestCaptureContentFromSSE:
    """Test SSE event capture for session persistence."""

    def test_capture_thinking_delta_with_signature(self) -> None:
        """Thinking delta with signature field captures signature."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: thinking_delta\n"
            'data: {"messageId": "m1", "signature": "EqoB_sig", "blockIndex": 0}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "thinking_0" in blocks
        assert blocks["thinking_0"]["signature"] == "EqoB_sig"

    def test_capture_thinking_delta_text(self) -> None:
        """Thinking delta with text accumulates content."""
        blocks: dict[str, dict[str, Any]] = {}
        sse1 = 'event: thinking_delta\ndata: {"messageId": "m1", "delta": "Let me ", "blockIndex": 0}\n\n'
        sse2 = 'event: thinking_delta\ndata: {"messageId": "m1", "delta": "think...", "blockIndex": 0}\n\n'
        capture_content_from_sse(sse1, blocks)
        capture_content_from_sse(sse2, blocks)

        assert blocks["thinking_0"]["thinking"] == "Let me think..."

    def test_capture_tool_use(self) -> None:
        """Tool use events are captured with correct structure."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: tool_use\n"
            'data: {"toolCallId": "t1", "toolName": "extract_issues", "toolInput": {"note_id": "n1"}}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "tool_use_t1" in blocks
        assert blocks["tool_use_t1"]["name"] == "extract_issues"

    def test_capture_tool_result_error(self) -> None:
        """Failed tool results capture error state."""
        blocks: dict[str, dict[str, Any]] = {}
        sse = (
            "event: tool_result\n"
            'data: {"toolCallId": "t1", "status": "failed", "errorMessage": "No such tool"}\n\n'
        )
        capture_content_from_sse(sse, blocks)

        assert "tool_result_t1" in blocks
        assert blocks["tool_result_t1"]["is_error"] is True


class TestExtractQuestionDataFromBlocks:
    """Test extraction of question_data from content_blocks for session persistence."""

    def test_returns_none_when_no_ask_user_blocks(self) -> None:
        """Normal content blocks without ask_user return None."""
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello", "index": 0},
            "tool_use_t1": {
                "type": "tool_use",
                "id": "t1",
                "name": "extract_issues",
                "input": {},
                "index": 1,
            },
        }
        assert extract_question_data_from_blocks(blocks) is None

    def test_returns_none_for_empty_blocks(self) -> None:
        """Empty content blocks return None."""
        assert extract_question_data_from_blocks({}) is None

    def test_returns_none_for_non_pending_answer_tool_result(self) -> None:
        """Tool results without pending_answer status return None."""
        blocks: dict[str, dict[str, Any]] = {
            "tool_result_t1": {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": '{"status": "success", "data": "ok"}',
                "is_error": False,
                "index": 0,
            },
        }
        assert extract_question_data_from_blocks(blocks) is None

    def test_extracts_question_data_from_pending_answer(self) -> None:
        """Extracts question_data when ask_user tool_result has pending_answer."""
        from uuid import uuid4

        from pilot_space.ai.sdk.question_adapter import QuestionAdapter

        # Register a question in the adapter
        adapter = QuestionAdapter()
        test_user_id = uuid4()
        question_id, _ = adapter.register_question(
            message_id="msg_1",
            tool_call_id="tool_1",
            questions=[
                {
                    "question": "Pick approach?",
                    "options": [
                        {"label": "A", "description": "First"},
                        {"label": "B", "description": "Second"},
                    ],
                    "header": "Approach",
                }
            ],
            user_id=test_user_id,
        )

        # Build content_blocks with a matching tool_result
        import json

        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Let me ask...", "index": 0},
            "tool_result_ask": {
                "type": "tool_result",
                "tool_use_id": "ask_user_call",
                "content": json.dumps(
                    {
                        "status": "pending_answer",
                        "questionId": str(question_id),
                        "message": "Questions displayed.",
                    }
                ),
                "is_error": False,
                "index": 1,
            },
        }

        # Patch the module-level adapter
        import pilot_space.ai.sdk.question_adapter as qa_module

        original = qa_module._default_adapter
        qa_module._default_adapter = adapter
        try:
            result = extract_question_data_from_blocks(blocks)
        finally:
            qa_module._default_adapter = original

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["questionId"] == str(question_id)
        assert len(result[0]["questions"]) == 1
        assert result[0]["questions"][0]["question"] == "Pick approach?"
        assert "answers" not in result[0]  # No answers at ask-time

    def test_returns_none_when_question_not_in_adapter(self) -> None:
        """Returns None if questionId not found in QuestionAdapter."""
        import json
        from uuid import uuid4

        blocks: dict[str, dict[str, Any]] = {
            "tool_result_ask": {
                "type": "tool_result",
                "tool_use_id": "ask_user_call",
                "content": json.dumps(
                    {
                        "status": "pending_answer",
                        "questionId": str(uuid4()),
                        "message": "Questions displayed.",
                    }
                ),
                "is_error": False,
                "index": 0,
            },
        }

        result = extract_question_data_from_blocks(blocks)
        assert result is None

    def test_extracts_question_data_from_dict_content(self) -> None:
        """Extracts question_data when tool_result content is a dict (SSE capture format)."""
        from uuid import uuid4

        from pilot_space.ai.sdk.question_adapter import QuestionAdapter

        adapter = QuestionAdapter()
        test_user_id = uuid4()
        question_id, _ = adapter.register_question(
            message_id="msg_2",
            tool_call_id="tool_2",
            questions=[
                {
                    "question": "Which DB?",
                    "options": [
                        {"label": "Postgres", "description": "Relational"},
                        {"label": "Mongo", "description": "Document"},
                    ],
                    "header": "Database",
                }
            ],
            user_id=test_user_id,
        )

        # Content as dict (how SSE capture actually stores it)
        blocks: dict[str, dict[str, Any]] = {
            "tool_result_ask": {
                "type": "tool_result",
                "tool_use_id": "ask_user_call",
                "content": {
                    "status": "pending_answer",
                    "questionId": str(question_id),
                    "message": "Questions displayed.",
                },
                "is_error": False,
                "index": 0,
            },
        }

        import pilot_space.ai.sdk.question_adapter as qa_module

        original = qa_module._default_adapter
        qa_module._default_adapter = adapter
        try:
            result = extract_question_data_from_blocks(blocks)
        finally:
            qa_module._default_adapter = original

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["questionId"] == str(question_id)
        assert len(result[0]["questions"]) == 1
        assert result[0]["questions"][0]["question"] == "Which DB?"

    def test_extracts_multiple_question_data_as_list(self) -> None:
        """Extracts multiple pending_answer blocks into a list."""
        import json
        from uuid import uuid4

        from pilot_space.ai.sdk.question_adapter import QuestionAdapter

        adapter = QuestionAdapter()
        test_user_id = uuid4()

        q1_id, _ = adapter.register_question(
            message_id="msg_1",
            tool_call_id="tool_1",
            questions=[{"question": "Q1?", "options": [{"label": "A"}], "header": "H1"}],
            user_id=test_user_id,
        )
        q2_id, _ = adapter.register_question(
            message_id="msg_2",
            tool_call_id="tool_2",
            questions=[{"question": "Q2?", "options": [{"label": "B"}], "header": "H2"}],
            user_id=test_user_id,
        )

        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Let me ask...", "index": 0},
            "tool_result_ask1": {
                "type": "tool_result",
                "tool_use_id": "ask1",
                "content": json.dumps(
                    {
                        "status": "pending_answer",
                        "questionId": str(q1_id),
                        "message": "Q1 displayed.",
                    }
                ),
                "is_error": False,
                "index": 1,
            },
            "tool_result_ask2": {
                "type": "tool_result",
                "tool_use_id": "ask2",
                "content": json.dumps(
                    {
                        "status": "pending_answer",
                        "questionId": str(q2_id),
                        "message": "Q2 displayed.",
                    }
                ),
                "is_error": False,
                "index": 2,
            },
        }

        import pilot_space.ai.sdk.question_adapter as qa_module

        original = qa_module._default_adapter
        qa_module._default_adapter = adapter
        try:
            result = extract_question_data_from_blocks(blocks)
        finally:
            qa_module._default_adapter = original

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        question_ids = {r["questionId"] for r in result}
        assert str(q1_id) in question_ids
        assert str(q2_id) in question_ids

    def test_handles_malformed_json_gracefully(self) -> None:
        """Malformed JSON in tool_result content is handled gracefully."""
        blocks: dict[str, dict[str, Any]] = {
            "tool_result_ask": {
                "type": "tool_result",
                "tool_use_id": "ask_user_call",
                "content": "not valid json pending_answer",
                "is_error": False,
                "index": 0,
            },
        }
        assert extract_question_data_from_blocks(blocks) is None


class TestClassifyEffort:
    """Test effort classification for SDK configuration."""

    def test_greeting_is_low(self) -> None:
        assert classify_effort("hello") == "low"

    def test_long_message_is_high(self) -> None:
        assert classify_effort("x" * 201) == "high"

    def test_complex_keyword_is_high(self) -> None:
        assert classify_effort("please analyze the codebase") == "high"

    def test_normal_message_is_none(self) -> None:
        assert classify_effort("update the title of this note") is None


class TestDetectSkill:
    """Test slash-command skill detection."""

    def test_detects_slash_command(self) -> None:
        assert detect_skill_from_message("/extract-issues from this note") == "extract-issues"

    def test_no_slash_returns_none(self) -> None:
        assert detect_skill_from_message("extract issues from this note") is None

    def test_empty_slash_returns_none(self) -> None:
        assert detect_skill_from_message("/") is None


# ---------------------------------------------------------------------------
# merge_sdk_and_queue
# ---------------------------------------------------------------------------


async def _async_iter_from_list(items: list[Any]):
    """Helper: create an async iterator from a list."""
    for item in items:
        yield item


class TestMergeSdkAndQueue:
    """Test concurrent SDK + queue stream merge."""

    @pytest.mark.asyncio
    async def test_sdk_items_yielded_as_sdk_source(self) -> None:
        """SDK messages appear with source='sdk'."""
        sdk_iter = _async_iter_from_list(["msg1", "msg2"])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        assert ("sdk", "msg1") in results
        assert ("sdk", "msg2") in results

    @pytest.mark.asyncio
    async def test_queue_items_yielded_as_queue_source(self) -> None:
        """Queue events appear with source='queue'."""
        sdk_iter = _async_iter_from_list(["msg1"])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()
        await tool_queue.put("approval_event_sse")

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        assert ("queue", "approval_event_sse") in results
        assert ("sdk", "msg1") in results

    @pytest.mark.asyncio
    async def test_finishes_when_sdk_exhausted(self) -> None:
        """Generator stops when SDK iterator is done, even if queue has items."""
        sdk_iter = _async_iter_from_list([])
        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results = []
        async for source, item in merge_sdk_and_queue(sdk_iter, tool_queue):
            results.append((source, item))

        # Should terminate with no items since SDK is empty
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_interleaved_sdk_and_queue(self) -> None:
        """SDK and queue items can interleave."""

        async def _slow_sdk():
            yield "sdk_1"
            await asyncio.sleep(0.05)
            yield "sdk_2"

        tool_queue: asyncio.Queue[str] = asyncio.Queue()

        results: list[tuple[str, Any]] = []

        async def _producer():
            await asyncio.sleep(0.02)
            await tool_queue.put("queue_event")

        producer_task = asyncio.create_task(_producer())

        async for source, item in merge_sdk_and_queue(_slow_sdk(), tool_queue):
            results.append((source, item))

        await producer_task

        sources = [s for s, _ in results]
        assert "sdk" in sources
        assert "queue" in sources


class TestExtractToolCallsFromBlocks:
    """Test tool call extraction from content blocks."""

    def test_returns_none_for_empty_blocks(self) -> None:
        assert extract_tool_calls_from_blocks({}) is None

    def test_returns_none_when_no_tool_use(self) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "text_0": {"type": "text", "text": "Hello", "index": 0},
        }
        assert extract_tool_calls_from_blocks(blocks) is None

    def test_extracts_single_tool_call_with_result(self) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_abc": {
                "type": "tool_use",
                "id": "abc",
                "name": "get_issue",
                "input": {"issue_id": "123"},
                "index": 0,
            },
            "tool_result_abc": {
                "type": "tool_result",
                "tool_use_id": "abc",
                "content": {"title": "Fix bug"},
                "is_error": False,
                "index": 1,
            },
        }
        result = extract_tool_calls_from_blocks(blocks)
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "abc"
        assert result[0]["name"] == "get_issue"
        assert result[0]["input"] == {"issue_id": "123"}
        assert result[0]["status"] == "completed"
        assert result[0]["output"] == {"title": "Fix bug"}

    def test_extracts_failed_tool_call(self) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_xyz": {
                "type": "tool_use",
                "id": "xyz",
                "name": "delete_issue",
                "input": {},
                "index": 0,
            },
            "tool_result_xyz": {
                "type": "tool_result",
                "tool_use_id": "xyz",
                "content": "Permission denied",
                "is_error": True,
                "index": 1,
            },
        }
        result = extract_tool_calls_from_blocks(blocks)
        assert result is not None
        assert result[0]["status"] == "failed"
        assert result[0]["error_message"] == "Permission denied"

    def test_tool_use_without_result_is_pending(self) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_noresult": {
                "type": "tool_use",
                "id": "noresult",
                "name": "search",
                "input": {"q": "test"},
                "index": 0,
            },
        }
        result = extract_tool_calls_from_blocks(blocks)
        assert result is not None
        assert result[0]["status"] == "pending"
        assert "output" not in result[0]

    def test_extracts_multiple_tool_calls(self) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "tool_use_a": {
                "type": "tool_use",
                "id": "a",
                "name": "get_issue",
                "input": {},
                "index": 0,
            },
            "tool_result_a": {
                "type": "tool_result",
                "tool_use_id": "a",
                "content": "ok",
                "is_error": False,
                "index": 1,
            },
            "tool_use_b": {
                "type": "tool_use",
                "id": "b",
                "name": "update_issue",
                "input": {"title": "new"},
                "index": 2,
            },
            "tool_result_b": {
                "type": "tool_result",
                "tool_use_id": "b",
                "content": "done",
                "is_error": False,
                "index": 3,
            },
        }
        result = extract_tool_calls_from_blocks(blocks)
        assert result is not None
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"get_issue", "update_issue"}


class TestGetWorkspaceEmbeddingKey:
    """Test renamed get_workspace_embedding_key and backward-compat alias."""

    def test_alias_points_to_same_function(self) -> None:
        """get_workspace_openai_key is an alias for get_workspace_embedding_key."""
        assert get_workspace_openai_key is get_workspace_embedding_key


# ---------------------------------------------------------------------------
# _build_server_config — shlex tokenisation for NPX/UVX commands
# ---------------------------------------------------------------------------


class TestBuildServerConfigArgvTokenisation:
    """Verify that _build_server_config uses shlex.split for NPX/UVX commands.

    str.split() breaks quoted arguments ('--name "foo bar"' → wrong argv).
    shlex.split(posix=True) produces the correct POSIX token list.
    """

    def _make_npx_server(
        self,
        url_or_command: str | None,
        command_args: str | None = None,
        env_vars_encrypted: str | None = None,
    ) -> Any:
        from unittest.mock import MagicMock

        from pilot_space.infrastructure.database.models.workspace_mcp_server import (
            McpCommandRunner,
            McpServerType,
            McpTransport,
            WorkspaceMcpServer,
        )

        server = MagicMock(spec=WorkspaceMcpServer)
        server.server_type = McpServerType.COMMAND
        server.command_runner = McpCommandRunner.NPX
        server.transport = McpTransport.STDIO
        server.url_or_command = url_or_command
        server.command_args = command_args
        server.env_vars_encrypted = env_vars_encrypted
        server.id = "test-server-id"
        return server

    def _build(self, server: Any) -> Any:
        from pilot_space.ai.agents.pilotspace_stream_utils import _build_server_config

        return _build_server_config(server, decrypt_fn=lambda _: "token")

    def test_simple_command_no_args(self) -> None:
        """command_runner=npx, url_or_command='my-pkg' → command='npx', args=['my-pkg']"""
        server = self._make_npx_server("my-pkg")
        config = self._build(server)
        assert config is not None
        assert config["command"] == "npx"
        assert config.get("args") == ["my-pkg"]

    def test_quoted_argument_preserved_as_single_token(self) -> None:
        """Quoted arg must not be split: url_or_command='--name "foo bar" --flag' → args=['--name', 'foo bar', '--flag']"""
        server = self._make_npx_server('--name "foo bar" --flag')
        config = self._build(server)
        assert config is not None
        assert config["command"] == "npx"
        assert config.get("args") == ["--name", "foo bar", "--flag"]

    def test_single_quoted_argument_preserved(self) -> None:
        """Single-quoted arg: url_or_command=\"--key 'hello world'\" → args=['--key', 'hello world']"""
        server = self._make_npx_server("--key 'hello world'")
        config = self._build(server)
        assert config is not None
        assert config.get("args") == ["--key", "hello world"]

    def test_command_args_quoted_token_preserved(self) -> None:
        """Quoted token in command_args must also be a single argv element."""
        server = self._make_npx_server("my-pkg", command_args='--title "my title"')
        config = self._build(server)
        assert config is not None
        # args come from both url_or_command and command_args
        args = config.get("args", [])
        assert "my-pkg" in args
        assert "--title" in args
        assert "my title" in args  # must be a single token
        assert '"my title"' not in args  # must NOT contain the quotes themselves

    def test_command_only_no_args(self) -> None:
        """No url_or_command → command='npx', no args."""
        server = self._make_npx_server(None)
        config = self._build(server)
        assert config is not None
        assert config["command"] == "npx"
        assert not config.get("args")

    def test_malformed_quotes_returns_none(self) -> None:
        """Unterminated quote is a parse error — config returns None instead of crashing."""
        server = self._make_npx_server('--name "unterminated')
        config = self._build(server)
        assert config is None

    def test_malformed_command_args_returns_none(self) -> None:
        """Unterminated quote in command_args returns None."""
        server = self._make_npx_server("my-pkg", command_args="--flag 'unterminated")
        config = self._build(server)
        assert config is None
