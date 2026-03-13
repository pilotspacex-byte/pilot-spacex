"""Unit tests for the spaces module.

Tests cover:
- SpaceContext dataclass and properties
- LocalFileSystemSpace lifecycle
- ProjectBootstrapper hydration
- SpaceManager factory service
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from pilot_space.spaces.base import SpaceContext
from pilot_space.spaces.bootstrapper import ProjectBootstrapper
from pilot_space.spaces.local import LocalFileSystemSpace
from pilot_space.spaces.manager import SpaceManager, create_space_manager


class TestSpaceContext:
    """Tests for SpaceContext dataclass."""

    def test_space_context_initialization(self) -> None:
        """Test SpaceContext can be initialized with required fields."""
        ctx = SpaceContext(id="test:user", path=Path("/tmp/test"))

        assert ctx.id == "test:user"
        assert ctx.path == Path("/tmp/test")
        assert ctx.env == {}

    def test_space_context_with_env(self) -> None:
        """Test SpaceContext accepts environment variables."""
        env = {"WORKSPACE_ID": "ws-123", "USER_ID": "user-456"}
        ctx = SpaceContext(id="test:user", path=Path("/tmp/test"), env=env)

        assert ctx.env == env
        assert ctx.env["WORKSPACE_ID"] == "ws-123"

    def test_claude_dir_property(self) -> None:
        """Test claude_dir property returns correct path."""
        ctx = SpaceContext(id="test", path=Path("/workspace"))

        assert ctx.claude_dir == Path("/workspace/.claude")

    def test_skills_dir_property(self) -> None:
        """Test skills_dir property returns correct path."""
        ctx = SpaceContext(id="test", path=Path("/workspace"))

        assert ctx.skills_dir == Path("/workspace/.claude/skills")

    def test_commands_dir_property(self) -> None:
        """Test commands_dir property returns correct path."""
        ctx = SpaceContext(id="test", path=Path("/workspace"))

        assert ctx.commands_dir == Path("/workspace/.claude/commands")

    def test_rules_dir_property(self) -> None:
        """Test rules_dir property returns correct path."""
        ctx = SpaceContext(id="test", path=Path("/workspace"))

        assert ctx.rules_dir == Path("/workspace/.claude/rules")

    def test_hooks_file_property(self) -> None:
        """Test hooks_file property returns correct path."""
        ctx = SpaceContext(id="test", path=Path("/workspace"))

        assert ctx.hooks_file == Path("/workspace/.claude/hooks.json")

    def test_to_sdk_env_includes_space_context(self) -> None:
        """Test to_sdk_env includes space ID and path."""
        ctx = SpaceContext(
            id="ws:user",
            path=Path("/workspace"),
            env={"CUSTOM": "value"},
        )

        sdk_env = ctx.to_sdk_env()

        assert sdk_env["PILOT_SPACE_ID"] == "ws:user"
        assert sdk_env["PILOT_SPACE_PATH"] == "/workspace"
        assert sdk_env["CUSTOM"] == "value"


class TestProjectBootstrapper:
    """Tests for ProjectBootstrapper."""

    @pytest.fixture
    def temp_templates_dir(self) -> Path:
        """Create a temporary templates directory with sample content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = Path(tmpdir)

            # Create skills directory with sample skill
            skills_dir = templates / "skills" / "test-skill"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\nname: test-skill\ndescription: Test\n---\n# Test Skill"
            )

            # Create rules directory
            rules_dir = templates / "rules"
            rules_dir.mkdir()
            (rules_dir / "test-rule.md").write_text("# Test Rule")

            # Create CLAUDE.md
            (templates / "CLAUDE.md").write_text("# Claude Instructions")

            yield templates

    @pytest.fixture
    def temp_target_dir(self) -> Path:
        """Create a temporary target directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_hydrate_creates_claude_directory(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate creates .claude directory in target."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        await bootstrapper.hydrate(temp_target_dir)

        assert (temp_target_dir / ".claude").exists()
        assert (temp_target_dir / ".claude").is_dir()

    @pytest.mark.asyncio
    async def test_hydrate_copies_skills(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate copies skills to target."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        await bootstrapper.hydrate(temp_target_dir)

        skill_file = temp_target_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
        assert skill_file.exists()
        assert "test-skill" in skill_file.read_text()

    @pytest.mark.asyncio
    async def test_hydrate_copies_rules(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate copies rules to target."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        await bootstrapper.hydrate(temp_target_dir)

        rule_file = temp_target_dir / ".claude" / "rules" / "test-rule.md"
        assert rule_file.exists()

    @pytest.mark.asyncio
    async def test_hydrate_copies_claude_md(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate copies CLAUDE.md to target."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        await bootstrapper.hydrate(temp_target_dir)

        claude_file = temp_target_dir / ".claude" / "CLAUDE.md"
        assert claude_file.exists()
        assert "Claude Instructions" in claude_file.read_text()

    @pytest.mark.asyncio
    async def test_claude_md_includes_note_tools(self, temp_target_dir: Path) -> None:
        """Test CLAUDE.md template includes note tool instructions."""
        # Use the real template from the source
        from pilot_space.ai.templates import CLAUDE_MD_PATH

        bootstrapper = ProjectBootstrapper(CLAUDE_MD_PATH.parent)
        await bootstrapper.hydrate(temp_target_dir)

        claude_file = temp_target_dir / ".claude" / "CLAUDE.md"
        content = claude_file.read_text()

        # Verify note tools section exists
        assert "### Note Tools (7 tools)" in content

        # Verify all 7 note tools are documented
        assert "summarize_note(note_id)" in content
        assert "update_note_block(note_id, block_id, new_content_markdown, operation)" in content
        assert "enhance_text(note_id, block_id, enhanced_markdown)" in content
        assert "extract_issues(note_id, block_ids, issues)" in content
        assert (
            "create_issue_from_note(note_id, block_id, title, description, priority, issue_type)"
            in content
        )
        assert "link_existing_issues(note_id, search_query, workspace_id)" in content

        # Verify workflow guidance exists
        assert "Note Tools Workflow" in content
        assert "Always call this first" in content

    @pytest.mark.asyncio
    async def test_claude_md_tool_names_match_registered_tools(self, temp_target_dir: Path) -> None:
        """Test CLAUDE.md tool names match tools registered in MCP servers."""
        from pilot_space.ai.templates import CLAUDE_MD_PATH

        bootstrapper = ProjectBootstrapper(CLAUDE_MD_PATH.parent)
        await bootstrapper.hydrate(temp_target_dir)

        claude_file = temp_target_dir / ".claude" / "CLAUDE.md"
        content = claude_file.read_text()

        # Tool names from note_server.py MCP server registration
        expected_tools = [
            "update_note_block",
            "enhance_text",
            "extract_issues",
            "create_issue_from_note",
            "link_existing_issues",
            "write_to_note",
        ]

        for tool_name in expected_tools:
            assert tool_name in content, f"Tool {tool_name} not found in CLAUDE.md"

    @pytest.mark.asyncio
    async def test_hydrate_is_idempotent(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate can be called multiple times safely."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        # First hydration
        await bootstrapper.hydrate(temp_target_dir)

        # Create user content
        user_skill = temp_target_dir / ".claude" / "skills" / "user-skill"
        user_skill.mkdir(parents=True)
        (user_skill / "SKILL.md").write_text("# User Skill")

        # Second hydration
        await bootstrapper.hydrate(temp_target_dir)

        # User content preserved
        assert (user_skill / "SKILL.md").exists()
        # System content still present
        assert (temp_target_dir / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()

    @pytest.mark.asyncio
    async def test_hydrate_with_missing_templates_dir(self, temp_target_dir: Path) -> None:
        """Test hydrate handles missing templates directory gracefully."""
        bootstrapper = ProjectBootstrapper(Path("/nonexistent/path"))

        # Should not raise, just log warning
        await bootstrapper.hydrate(temp_target_dir)

        # .claude directory created but empty
        assert (temp_target_dir / ".claude").exists()

    @pytest.mark.asyncio
    async def test_hydrate_skill_single_skill(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate_skill copies a single skill."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        result = await bootstrapper.hydrate_skill("test-skill", temp_target_dir)

        assert result is True
        skill_file = temp_target_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
        assert skill_file.exists()

    @pytest.mark.asyncio
    async def test_hydrate_skill_nonexistent(
        self, temp_templates_dir: Path, temp_target_dir: Path
    ) -> None:
        """Test hydrate_skill returns False for nonexistent skill."""
        bootstrapper = ProjectBootstrapper(temp_templates_dir)

        result = await bootstrapper.hydrate_skill("nonexistent-skill", temp_target_dir)

        assert result is False


class TestLocalFileSystemSpace:
    """Tests for LocalFileSystemSpace."""

    @pytest.fixture
    def temp_storage_root(self) -> Path:
        """Create temporary storage root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_templates_dir(self) -> Path:
        """Create minimal templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = Path(tmpdir)
            (templates / "CLAUDE.md").write_text("# Test")
            yield templates

    @pytest.fixture
    def bootstrapper(self, temp_templates_dir: Path) -> ProjectBootstrapper:
        """Create bootstrapper with temp templates."""
        return ProjectBootstrapper(temp_templates_dir)

    @pytest.mark.asyncio
    async def test_prepare_creates_space_directory(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test prepare creates workspace directory."""
        workspace_id = uuid4()
        user_id = uuid4()

        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=workspace_id,
            user_id=user_id,
            bootstrapper=bootstrapper,
        )

        context = await space.prepare()

        assert context.path.exists()
        assert str(workspace_id) in str(context.path)
        assert str(user_id) in str(context.path)

    @pytest.mark.asyncio
    async def test_prepare_returns_valid_context(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test prepare returns correctly populated SpaceContext."""
        workspace_id = uuid4()
        user_id = uuid4()

        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=workspace_id,
            user_id=user_id,
            bootstrapper=bootstrapper,
        )

        context = await space.prepare()

        assert context.id == f"{workspace_id}:{user_id}"
        assert context.env["PILOT_WORKSPACE_ID"] == str(workspace_id)
        assert context.env["PILOT_USER_ID"] == str(user_id)
        assert context.env["PILOT_SPACE_TYPE"] == "local"

    @pytest.mark.asyncio
    async def test_prepare_hydrates_claude_directory(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test prepare hydrates .claude directory."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        context = await space.prepare()

        assert context.claude_dir.exists()
        assert (context.claude_dir / "CLAUDE.md").exists()

    @pytest.mark.asyncio
    async def test_cleanup_clears_context(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test cleanup clears internal context."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        await space.prepare()
        await space.cleanup()

        # Internal context cleared but directory persists
        assert space._context is None
        assert space.space_path.exists()

    @pytest.mark.asyncio
    async def test_session_context_manager(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test session() async context manager works correctly."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        async with space.session() as context:
            assert context.path.exists()
            assert context.id is not None

        # After context exits, cleanup was called
        assert space._context is None

    def test_exists_returns_false_for_new_space(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test exists() returns False for unprepared space."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        assert space.exists() is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_after_prepare(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test exists() returns True after prepare()."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        await space.prepare()

        assert space.exists() is True

    @pytest.mark.asyncio
    async def test_delete_removes_space_directory(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test delete() removes the workspace directory."""
        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=uuid4(),
            user_id=uuid4(),
            bootstrapper=bootstrapper,
        )

        await space.prepare()
        assert space.exists() is True

        await space.delete()
        assert space.exists() is False

    def test_space_path_property(
        self, temp_storage_root: Path, bootstrapper: ProjectBootstrapper
    ) -> None:
        """Test space_path property returns correct path."""
        workspace_id = uuid4()
        user_id = uuid4()

        space = LocalFileSystemSpace(
            storage_root=temp_storage_root,
            workspace_id=workspace_id,
            user_id=user_id,
            bootstrapper=bootstrapper,
        )

        expected = temp_storage_root / str(workspace_id) / str(user_id)
        assert space.space_path == expected


class TestSpaceManager:
    """Tests for SpaceManager factory service."""

    @pytest.fixture
    def temp_dirs(self) -> tuple[Path, Path]:
        """Create temp storage root and templates directory."""
        import tempfile

        with (
            tempfile.TemporaryDirectory() as storage_root,
            tempfile.TemporaryDirectory() as templates,
        ):
            templates_path = Path(templates)
            (templates_path / "CLAUDE.md").write_text("# Test")
            yield Path(storage_root), templates_path

    @pytest.fixture
    def manager(self, temp_dirs: tuple[Path, Path]) -> SpaceManager:
        """Create SpaceManager with temp directories."""
        storage_root, templates = temp_dirs
        bootstrapper = ProjectBootstrapper(templates)
        return SpaceManager(bootstrapper, storage_root=storage_root)

    def test_get_space_returns_local_filesystem_space(self, manager: SpaceManager) -> None:
        """Test get_space returns LocalFileSystemSpace in local mode."""
        space = manager.get_space(uuid4(), uuid4())

        assert isinstance(space, LocalFileSystemSpace)

    def test_get_space_with_container_mode_raises(self, temp_dirs: tuple[Path, Path]) -> None:
        """Test get_space raises NotImplementedError for container mode."""
        storage_root, templates = temp_dirs
        bootstrapper = ProjectBootstrapper(templates)
        manager = SpaceManager(
            bootstrapper,
            storage_root=storage_root,
            deployment_mode="container",
        )

        with pytest.raises(NotImplementedError, match="ContainerSpace"):
            manager.get_space(uuid4(), uuid4())

    def test_deployment_mode_property(self, manager: SpaceManager) -> None:
        """Test deployment_mode property returns configured mode."""
        assert manager.deployment_mode == "local"

    def test_storage_root_property(
        self, manager: SpaceManager, temp_dirs: tuple[Path, Path]
    ) -> None:
        """Test storage_root property returns configured path."""
        storage_root, _ = temp_dirs
        assert manager.storage_root == storage_root

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(self, manager: SpaceManager) -> None:
        """Test list_workspaces returns empty list when no spaces exist."""
        workspaces = manager.list_workspaces()
        assert workspaces == []

    @pytest.mark.asyncio
    async def test_list_workspaces_after_creating_spaces(self, manager: SpaceManager) -> None:
        """Test list_workspaces returns workspace IDs after creation."""
        ws1 = uuid4()
        ws2 = uuid4()
        user = uuid4()

        # Create two spaces in different workspaces
        space1 = manager.get_space(ws1, user)
        await space1.prepare()

        space2 = manager.get_space(ws2, user)
        await space2.prepare()

        workspaces = manager.list_workspaces()

        assert len(workspaces) == 2
        assert ws1 in workspaces
        assert ws2 in workspaces

    @pytest.mark.asyncio
    async def test_list_user_spaces(self, manager: SpaceManager) -> None:
        """Test list_user_spaces returns user IDs in a workspace."""
        ws = uuid4()
        user1 = uuid4()
        user2 = uuid4()

        # Create two spaces for different users
        space1 = manager.get_space(ws, user1)
        await space1.prepare()

        space2 = manager.get_space(ws, user2)
        await space2.prepare()

        users = manager.list_user_spaces(ws)

        assert len(users) == 2
        assert user1 in users
        assert user2 in users

    @pytest.mark.asyncio
    async def test_get_existing_space_returns_none_for_new(self, manager: SpaceManager) -> None:
        """Test get_existing_space returns None for non-existent space."""
        result = manager.get_existing_space(uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_existing_space_returns_space_if_exists(self, manager: SpaceManager) -> None:
        """Test get_existing_space returns space if it exists."""
        ws = uuid4()
        user = uuid4()

        # Create space
        space = manager.get_space(ws, user)
        await space.prepare()

        # Get existing
        existing = manager.get_existing_space(ws, user)

        assert existing is not None
        assert isinstance(existing, LocalFileSystemSpace)


class TestCreateSpaceManager:
    """Tests for create_space_manager factory function."""

    def test_create_space_manager_with_custom_templates(self) -> None:
        """Test factory function accepts custom templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = Path(tmpdir)
            (templates / "CLAUDE.md").write_text("# Test")

            manager = create_space_manager(templates)

            assert manager is not None
            assert isinstance(manager, SpaceManager)
