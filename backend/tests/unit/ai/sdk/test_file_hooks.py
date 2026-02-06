"""Unit tests for file-based hooks support.

Tests cover:
- HookResponse parsing and serialization
- HookDefinition configuration
- HookMatcher pattern matching
- HooksConfiguration loading
- FileBasedHookExecutor execution
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pilot_space.ai.sdk.file_hooks import (
    FileBasedHookExecutor,
    HookDefinition,
    HookMatcher,
    HookResponse,
    HooksConfiguration,
    HookType,
    PermissionDecision,
)


class TestHookResponse:
    """Tests for HookResponse dataclass."""

    def test_default_values(self) -> None:
        """Test HookResponse has correct defaults."""
        response = HookResponse()

        assert response.continue_execution is True
        assert response.stop_reason is None
        assert response.suppress_output is False
        assert response.permission_decision is None

    def test_from_json_simple(self) -> None:
        """Test parsing simple JSON response."""
        data = {"continue": True, "suppressOutput": False}

        response = HookResponse.from_json(data)

        assert response.continue_execution is True
        assert response.suppress_output is False

    def test_from_json_with_stop(self) -> None:
        """Test parsing JSON with stop reason."""
        data = {"continue": False, "stopReason": "Validation failed"}

        response = HookResponse.from_json(data)

        assert response.continue_execution is False
        assert response.stop_reason == "Validation failed"

    def test_from_json_with_permission(self) -> None:
        """Test parsing JSON with permission decision."""
        data = {
            "continue": True,
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "Protected file",
            },
        }

        response = HookResponse.from_json(data)

        assert response.permission_decision == PermissionDecision.DENY
        assert response.permission_reason == "Protected file"

    def test_from_json_with_updated_input(self) -> None:
        """Test parsing JSON with updated input."""
        data = {
            "continue": True,
            "hookSpecificOutput": {
                "updatedInput": {"path": "/modified/path"},
            },
        }

        response = HookResponse.from_json(data)

        assert response.updated_input == {"path": "/modified/path"}

    def test_to_dict_roundtrip(self) -> None:
        """Test to_dict produces valid JSON structure."""
        response = HookResponse(
            continue_execution=True,
            permission_decision=PermissionDecision.ASK,
            permission_reason="Needs approval",
            additional_context="Extra info",
        )

        data = response.to_dict()

        assert data["continue"] is True
        assert data["hookSpecificOutput"]["permissionDecision"] == "ask"
        assert data["hookSpecificOutput"]["permissionDecisionReason"] == "Needs approval"
        assert data["hookSpecificOutput"]["additionalContext"] == "Extra info"


class TestHookDefinition:
    """Tests for HookDefinition dataclass."""

    def test_from_dict_command(self) -> None:
        """Test parsing command hook definition."""
        data = {
            "type": "command",
            "command": "/scripts/validate.sh",
            "timeout": 60,
            "env": {"STRICT": "1"},
        }

        hook = HookDefinition.from_dict(data)

        assert hook.type == HookType.COMMAND
        assert hook.command == "/scripts/validate.sh"
        assert hook.timeout == 60
        assert hook.env == {"STRICT": "1"}

    def test_from_dict_deny(self) -> None:
        """Test parsing deny hook definition."""
        data = {
            "type": "deny",
            "patterns": [".env*", "*.pem"],
            "reason": "Protected file",
        }

        hook = HookDefinition.from_dict(data)

        assert hook.type == HookType.DENY
        assert ".env*" in hook.patterns
        assert hook.reason == "Protected file"

    def test_from_dict_approve(self) -> None:
        """Test parsing approve hook definition."""
        data = {
            "type": "approve",
            "condition": "path.startswith('src/')",
            "reason": "Outside src/ requires approval",
        }

        hook = HookDefinition.from_dict(data)

        assert hook.type == HookType.APPROVE
        assert hook.condition == "path.startswith('src/')"

    def test_default_timeout(self) -> None:
        """Test default timeout is 30 seconds."""
        data = {"type": "command", "command": "/scripts/test.sh"}

        hook = HookDefinition.from_dict(data)

        assert hook.timeout == 30


class TestHookMatcher:
    """Tests for HookMatcher pattern matching."""

    def test_exact_match(self) -> None:
        """Test exact tool name matching."""
        matcher = HookMatcher(matcher="Bash", hooks=[])

        assert matcher.matches("Bash") is True
        assert matcher.matches("Write") is False

    def test_or_pattern(self) -> None:
        """Test OR pattern matching."""
        matcher = HookMatcher(matcher="Write|Edit", hooks=[])

        assert matcher.matches("Write") is True
        assert matcher.matches("Edit") is True
        assert matcher.matches("Read") is False

    def test_glob_wildcard(self) -> None:
        """Test glob wildcard matching."""
        matcher = HookMatcher(matcher="*", hooks=[])

        assert matcher.matches("Bash") is True
        assert matcher.matches("Write") is True
        assert matcher.matches("AnyTool") is True

    def test_glob_prefix(self) -> None:
        """Test glob prefix matching."""
        matcher = HookMatcher(matcher="Web*", hooks=[])

        assert matcher.matches("WebFetch") is True
        assert matcher.matches("WebSearch") is True
        assert matcher.matches("Bash") is False

    def test_regex_pattern(self) -> None:
        """Test regex pattern matching."""
        matcher = HookMatcher(matcher="/^Web.*/", hooks=[])

        assert matcher.matches("WebFetch") is True
        assert matcher.matches("WebSearch") is True
        assert matcher.matches("Bash") is False

    def test_from_dict(self) -> None:
        """Test parsing matcher from dictionary."""
        data = {
            "matcher": "Bash",
            "description": "Validate bash commands",
            "hooks": [{"type": "command", "command": "/scripts/validate.sh"}],
        }

        matcher = HookMatcher.from_dict(data)

        assert matcher.matcher == "Bash"
        assert matcher.description == "Validate bash commands"
        assert len(matcher.hooks) == 1


class TestHooksConfiguration:
    """Tests for HooksConfiguration loading."""

    @pytest.fixture
    def sample_hooks_json(self) -> dict:
        """Sample hooks.json content."""
        return {
            "version": "1.0",
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "/scripts/validate.sh"}],
                    },
                    {
                        "matcher": "Write|Edit",
                        "hooks": [
                            {
                                "type": "deny",
                                "patterns": [".env*"],
                                "reason": "Protected",
                            }
                        ],
                    },
                ],
                "PostToolUse": [
                    {"matcher": "*", "hooks": [{"type": "log"}]},
                ],
            },
        }

    def test_from_dict(self, sample_hooks_json: dict) -> None:
        """Test parsing configuration from dictionary."""
        config = HooksConfiguration.from_dict(sample_hooks_json)

        assert config.version == "1.0"
        assert len(config.pre_tool_use) == 2
        assert len(config.post_tool_use) == 1

    def test_from_file(self, sample_hooks_json: dict) -> None:
        """Test loading configuration from file."""
        import json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_hooks_json, f)
            f.flush()

            config = HooksConfiguration.from_file(Path(f.name))

        assert config.version == "1.0"
        assert len(config.pre_tool_use) == 2

    def test_from_nonexistent_file(self) -> None:
        """Test loading from nonexistent file returns empty config."""
        config = HooksConfiguration.from_file(Path("/nonexistent/hooks.json"))

        assert config.version == "1.0"
        assert config.pre_tool_use == []

    def test_from_invalid_json(self) -> None:
        """Test loading from invalid JSON returns empty config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()

            config = HooksConfiguration.from_file(Path(f.name))

        assert config.pre_tool_use == []


class TestFileBasedHookExecutor:
    """Tests for FileBasedHookExecutor."""

    @pytest.fixture
    def temp_hooks_file(self) -> Path:
        """Create a temporary hooks.json file."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".claude"
            hooks_dir.mkdir()

            hooks_file = hooks_dir / "hooks.json"
            hooks_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Write|Edit",
                                    "hooks": [
                                        {
                                            "type": "deny",
                                            "patterns": [".env*", "*.pem"],
                                            "reason": "Protected file",
                                        }
                                    ],
                                },
                                {
                                    "matcher": "Write",
                                    "hooks": [
                                        {
                                            "type": "approve",
                                            "condition": "path.startswith('src/')",
                                            "reason": "Requires approval outside src/",
                                        }
                                    ],
                                },
                            ],
                        },
                    }
                )
            )

            yield hooks_file

    @pytest.fixture
    def executor(self, temp_hooks_file: Path) -> FileBasedHookExecutor:
        """Create executor with temp hooks file."""
        return FileBasedHookExecutor(temp_hooks_file)

    @pytest.mark.asyncio
    async def test_deny_hook_blocks_protected_file(self, executor: FileBasedHookExecutor) -> None:
        """Test deny hook blocks protected files."""
        response = await executor.execute_pre_tool_hooks("Write", {"path": ".env"})

        assert response.continue_execution is False
        assert response.permission_decision == PermissionDecision.DENY
        assert "Protected file" in (response.permission_reason or "")

    @pytest.mark.asyncio
    async def test_deny_hook_allows_normal_file(self, executor: FileBasedHookExecutor) -> None:
        """Test deny hook allows normal files."""
        response = await executor.execute_pre_tool_hooks("Write", {"path": "src/main.py"})

        # Should not be denied (but may require approval)
        assert (
            response.permission_decision != PermissionDecision.DENY
            or response.permission_decision is None
        )

    @pytest.mark.asyncio
    async def test_approve_hook_requires_approval_outside_src(
        self, executor: FileBasedHookExecutor
    ) -> None:
        """Test approve hook requires approval for files outside src/."""
        response = await executor.execute_pre_tool_hooks("Write", {"path": "config/settings.py"})

        assert response.permission_decision == PermissionDecision.ASK
        assert "approval" in (response.permission_reason or "").lower()

    @pytest.mark.asyncio
    async def test_approve_hook_allows_src_files(self, executor: FileBasedHookExecutor) -> None:
        """Test approve hook allows files in src/."""
        response = await executor.execute_pre_tool_hooks("Write", {"path": "src/main.py"})

        # Should not require approval for src/ files
        assert response.permission_decision != PermissionDecision.ASK

    @pytest.mark.asyncio
    async def test_no_matching_hooks(self, executor: FileBasedHookExecutor) -> None:
        """Test tools without matching hooks pass through."""
        response = await executor.execute_pre_tool_hooks("Read", {"path": "README.md"})

        assert response.continue_execution is True
        assert response.permission_decision is None

    def test_reload_refreshes_config(self, temp_hooks_file: Path) -> None:
        """Test reload refreshes configuration from file."""
        import json

        executor = FileBasedHookExecutor(temp_hooks_file)

        # Initial load
        assert len(executor.config.pre_tool_use) == 2

        # Modify file
        temp_hooks_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Bash", "hooks": []},
                        ],
                    },
                }
            )
        )

        # Reload
        executor.reload()

        assert len(executor.config.pre_tool_use) == 1
        assert executor.config.pre_tool_use[0].matcher == "Bash"


class TestConditionEvaluation:
    """Tests for condition expression evaluation."""

    @pytest.fixture
    def executor(self) -> FileBasedHookExecutor:
        """Create executor with minimal config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"hooks": {}}')
            f.flush()
            return FileBasedHookExecutor(Path(f.name))

    def test_startswith_condition(self, executor: FileBasedHookExecutor) -> None:
        """Test startswith condition evaluation."""
        assert executor._evaluate_condition("path.startswith('src/')", "src/main.py")
        assert not executor._evaluate_condition("path.startswith('src/')", "tests/test.py")

    def test_endswith_condition(self, executor: FileBasedHookExecutor) -> None:
        """Test endswith condition evaluation."""
        assert executor._evaluate_condition("path.endswith('.py')", "main.py")
        assert not executor._evaluate_condition("path.endswith('.py')", "main.js")

    def test_contains_condition(self, executor: FileBasedHookExecutor) -> None:
        """Test contains condition evaluation."""
        assert executor._evaluate_condition("path.contains('test')", "tests/test_main.py")
        assert not executor._evaluate_condition("path.contains('test')", "src/main.py")


class TestToSdkHooks:
    """Tests for to_sdk_hooks SDK callback generation."""

    @pytest.fixture
    def hooks_file(self) -> Path:
        """Create a temporary hooks.json file with various hooks."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / ".claude"
            hooks_dir.mkdir()

            hooks_file = hooks_dir / "hooks.json"
            hooks_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "deny",
                                            "patterns": ["*rm -rf*"],
                                            "reason": "Dangerous command blocked",
                                        }
                                    ],
                                },
                                {
                                    "matcher": "Write|Edit",
                                    "hooks": [
                                        {
                                            "type": "deny",
                                            "patterns": [".env*"],
                                            "reason": "Protected file",
                                        }
                                    ],
                                },
                            ],
                            "PostToolUse": [
                                {"matcher": "*", "hooks": [{"type": "log"}]},
                            ],
                        },
                    }
                )
            )

            yield hooks_file

    def test_to_sdk_hooks_returns_dict(self, hooks_file: Path) -> None:
        """Test to_sdk_hooks returns properly structured dict."""
        executor = FileBasedHookExecutor(hooks_file)
        sdk_hooks = executor.to_sdk_hooks()

        assert isinstance(sdk_hooks, dict)
        assert "PreToolUse" in sdk_hooks
        assert "PostToolUse" in sdk_hooks

    def test_to_sdk_hooks_structure(self, hooks_file: Path) -> None:
        """Test SDK hooks have correct structure with matcher and hooks."""
        executor = FileBasedHookExecutor(hooks_file)
        sdk_hooks = executor.to_sdk_hooks()

        # Check PreToolUse structure
        pre_hooks = sdk_hooks["PreToolUse"]
        assert len(pre_hooks) == 2

        # Each item should have matcher and hooks
        for hook_matcher in pre_hooks:
            assert "matcher" in hook_matcher
            assert "hooks" in hook_matcher
            assert isinstance(hook_matcher["hooks"], list)
            assert len(hook_matcher["hooks"]) == 1
            assert callable(hook_matcher["hooks"][0])

    def test_to_sdk_hooks_matchers_preserved(self, hooks_file: Path) -> None:
        """Test matcher patterns are preserved in SDK hooks."""
        executor = FileBasedHookExecutor(hooks_file)
        sdk_hooks = executor.to_sdk_hooks()

        matchers = [h["matcher"] for h in sdk_hooks["PreToolUse"]]
        assert "Bash" in matchers
        assert "Write|Edit" in matchers

    @pytest.mark.asyncio
    async def test_sdk_callback_deny_hook(self, hooks_file: Path) -> None:
        """Test generated SDK callback correctly denies dangerous commands."""
        executor = FileBasedHookExecutor(hooks_file)
        sdk_hooks = executor.to_sdk_hooks()

        # Find the Bash matcher callback
        bash_hook = next(h for h in sdk_hooks["PreToolUse"] if h["matcher"] == "Bash")
        callback = bash_hook["hooks"][0]

        # Simulate SDK calling the callback with dangerous command
        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }

        result = await callback(input_data, "test-id", None)

        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert (
            "Dangerous command blocked" in result["hookSpecificOutput"]["permissionDecisionReason"]
        )

    @pytest.mark.asyncio
    async def test_sdk_callback_allows_safe_command(self, hooks_file: Path) -> None:
        """Test generated SDK callback allows safe commands."""
        executor = FileBasedHookExecutor(hooks_file)
        sdk_hooks = executor.to_sdk_hooks()

        bash_hook = next(h for h in sdk_hooks["PreToolUse"] if h["matcher"] == "Bash")
        callback = bash_hook["hooks"][0]

        input_data = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }

        result = await callback(input_data, "test-id", None)

        # Empty result means allow
        assert result == {} or "permissionDecision" not in result.get("hookSpecificOutput", {})

    def test_empty_hooks_returns_empty_dict(self) -> None:
        """Test executor with no hooks returns empty dict."""
        import json

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"hooks": {}}, f)
            f.flush()

            executor = FileBasedHookExecutor(Path(f.name))
            sdk_hooks = executor.to_sdk_hooks()

            assert sdk_hooks == {}
