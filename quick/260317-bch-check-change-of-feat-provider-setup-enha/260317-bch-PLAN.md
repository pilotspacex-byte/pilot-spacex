---
phase: quick-260317-bch
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/src/pilot_space/ai/prompt/models.py
  - backend/src/pilot_space/ai/prompt/prompt_assembler.py
  - backend/src/pilot_space/ai/agents/pilotspace_agent.py
  - backend/tests/unit/ai/prompt/test_prompt_assembler.py
autonomous: true
requirements: [SKILL-PROMPT-01]

must_haves:
  truths:
    - "The agent system prompt contains a 'Your Skills' section listing the user's active skills by name and description"
    - "When the user has no active skills, no skills section appears in the prompt"
    - "The skills section is positioned between workspace context (layer 4) and session state (layer 5)"
    - "Each skill entry shows name and a short description so the agent can suggest skills proactively"
  artifacts:
    - path: "backend/src/pilot_space/ai/prompt/models.py"
      provides: "user_skills field on PromptLayerConfig"
      contains: "user_skills"
    - path: "backend/src/pilot_space/ai/prompt/prompt_assembler.py"
      provides: "_build_skills_section function and integration into assemble_system_prompt"
      contains: "_build_skills_section"
    - path: "backend/src/pilot_space/ai/agents/pilotspace_agent.py"
      provides: "Loading active user skills and passing to PromptLayerConfig"
      contains: "user_skills"
    - path: "backend/tests/unit/ai/prompt/test_prompt_assembler.py"
      provides: "Tests for skills prompt section"
      contains: "TestSkillsLayer"
  key_links:
    - from: "backend/src/pilot_space/ai/agents/pilotspace_agent.py"
      to: "UserSkillRepository.get_active_by_user_workspace"
      via: "db query in _build_stream_config"
      pattern: "user_skill_repo\\.get_active_by_user_workspace"
    - from: "backend/src/pilot_space/ai/agents/pilotspace_agent.py"
      to: "PromptLayerConfig"
      via: "user_skills kwarg"
      pattern: "user_skills="
    - from: "backend/src/pilot_space/ai/prompt/prompt_assembler.py"
      to: "PromptLayerConfig.user_skills"
      via: "_build_skills_section called in assemble_system_prompt"
      pattern: "_build_skills_section"
---

<objective>
Add user's active skills list to PilotSpace Agent's system prompt so the agent can proactively suggest relevant skills during conversation.

Purpose: The agent currently materializes skills to disk for Claude SDK auto-discovery but has no prompt-level awareness of what skills the user has. This means the agent cannot proactively suggest or reference skills. Adding a "Your Skills" section bridges this gap.

Output: Updated prompt assembler with skills layer, updated agent to pass skill data, tests verifying the new section.
</objective>

<execution_context>
@/Users/tindang/workspaces/tind-repo/pilot-space/.claude/get-shit-done/workflows/execute-plan.md
@/Users/tindang/workspaces/tind-repo/pilot-space/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/src/pilot_space/ai/prompt/models.py
@backend/src/pilot_space/ai/prompt/prompt_assembler.py
@backend/src/pilot_space/ai/agents/pilotspace_agent.py
@backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py
@backend/src/pilot_space/infrastructure/database/models/user_skill.py
@backend/tests/unit/ai/prompt/test_prompt_assembler.py

<interfaces>
<!-- Key types and contracts the executor needs. -->

From backend/src/pilot_space/ai/prompt/models.py:
```python
class PromptLayerConfig(BaseModel):
    base_prompt: str = ""
    role_type: str | None = None
    workspace_name: str | None = None
    project_names: list[str] | None = None
    user_message: str = ""
    has_note_context: bool = False
    memory_entries: list[dict[str, Any]] = Field(default_factory=list)
    graph_context: list[dict[str, Any]] = Field(default_factory=list)
    pending_approvals: int = 0
    budget_warning: str | None = None
    conversation_summary: str | None = None
```

From backend/src/pilot_space/ai/prompt/prompt_assembler.py:
```python
async def assemble_system_prompt(config: PromptLayerConfig) -> AssembledPrompt:
    # Layer 1: Identity (always)
    # Layer 2: Safety + tools + style (always)
    # Layer 3: Role adaptation (if role_type set)
    # Layer 4: Workspace context (if workspace/project info)
    # Layer 5: Session state (memory, summary, approvals, budget)
    # Layer 6: Intent-based rules (at end)
```

From backend/src/pilot_space/infrastructure/database/models/user_skill.py:
```python
class UserSkill(WorkspaceScopedModel):
    skill_name: Mapped[str | None]  # User-visible name
    skill_content: Mapped[str]       # SKILL.md-format markdown
    template_id: Mapped[uuid.UUID | None]
    is_active: Mapped[bool]
    template: Mapped[SkillTemplate | None]  # lazy="raise", needs selectinload
```

From backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py:
```python
class UserSkillRepository:
    async def get_active_by_user_workspace(self, user_id: UUID, workspace_id: UUID) -> Sequence[UserSkill]:
        # Returns active, non-deleted skills with template eagerly loaded
```

From backend/src/pilot_space/ai/agents/pilotspace_agent.py (_build_stream_config, lines 341-349):
```python
assembled = await assemble_system_prompt(
    PromptLayerConfig(
        role_type=_role_type,
        workspace_name=input_data.context.get("workspace_name"),
        project_names=input_data.context.get("project_names"),
        user_message=input_data.message,
        has_note_context="<note_context>" in input_data.message,
        graph_context=graph_context,
    )
)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add user_skills to PromptLayerConfig and build skills prompt section</name>
  <files>
    backend/src/pilot_space/ai/prompt/models.py,
    backend/src/pilot_space/ai/prompt/prompt_assembler.py,
    backend/tests/unit/ai/prompt/test_prompt_assembler.py
  </files>
  <behavior>
    - Test: When user_skills is empty list, no "Your Skills" section appears in prompt and "skills" not in layers_loaded
    - Test: When user_skills has entries, prompt contains "## Your Skills" section with each skill name and description
    - Test: When user_skills has entries, "skills" appears in layers_loaded
    - Test: Skills section is positioned between workspace context and session state (after layer 4, before layer 5)
    - Test: Skill entries display name and description in bullet format: "- **{name}**: {description}"
    - Test: Full assembly with user_skills includes the skills section alongside other layers
  </behavior>
  <action>
    1. In `models.py`, add a `user_skills` field to `PromptLayerConfig`:
       ```python
       user_skills: list[dict[str, str]] = Field(default_factory=list)
       ```
       Each dict has keys: `name` (str), `description` (str). Update the docstring to document the field.

    2. In `prompt_assembler.py`, add a `_build_skills_section` function:
       ```python
       def _build_skills_section(config: PromptLayerConfig) -> str | None:
           if not config.user_skills:
               return None
           lines = ["## Your Skills", "", "You have access to the following personalized skills:"]
           for skill in config.user_skills:
               name = skill.get("name", "Unknown")
               desc = skill.get("description", "")
               if desc:
                   lines.append(f"- **{name}**: {desc}")
               else:
                   lines.append(f"- **{name}**")
           lines.append("")
           lines.append("Proactively suggest relevant skills when they match the user's request.")
           return "\n".join(lines)
       ```

    3. In `assemble_system_prompt()`, insert skills section call between Layer 4 (workspace) and Layer 5 (session). Add after the workspace block (after line 95):
       ```python
       # Layer 4.5: User skills (between workspace and session)
       skills_section = _build_skills_section(config)
       if skills_section:
           sections.append(skills_section)
           layers_loaded.append("skills")
       ```

    4. In `test_prompt_assembler.py`, add a `TestSkillsLayer` class with tests for:
       - `test_with_user_skills`: passes 2 skills, asserts "Your Skills" in prompt, skill names present, "skills" in layers_loaded
       - `test_no_skills_skips_layer`: empty user_skills, asserts "Your Skills" not in prompt, "skills" not in layers_loaded
       - `test_skill_without_description`: skill dict with name only (empty desc), asserts name present without colon-description suffix
       - `test_skills_section_ordering`: asserts "Your Skills" appears after "Workspace Context" and before "Workspace Memory Context" or session content

    5. Update `TestFullAssembly.test_all_layers_loaded` to include `user_skills` in config and assert "Your Skills" in result.prompt.
  </action>
  <verify>
    <automated>cd /Users/tindang/workspaces/tind-repo/pilot-space/backend && uv run pytest tests/unit/ai/prompt/test_prompt_assembler.py -x -v 2>&1 | tail -40</automated>
  </verify>
  <done>
    - PromptLayerConfig has user_skills field (list of dicts with name/description)
    - _build_skills_section produces formatted "## Your Skills" markdown section
    - assemble_system_prompt includes skills between workspace and session layers
    - All new and existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire user skills from DB into PromptLayerConfig in _build_stream_config</name>
  <files>
    backend/src/pilot_space/ai/agents/pilotspace_agent.py
  </files>
  <action>
    In `_build_stream_config()` (line ~293), the method already loads user skills via `materialize_role_skills()` which uses `UserSkillRepository.get_active_by_user_workspace()`. However, the skill data is only used for disk materialization, not passed to the prompt.

    After `materialize_role_skills()` returns (line 298), add a query to load user skills for prompt injection. The `UserSkillRepository` is already imported in this method's scope (via the `_materialize_from_new_tables` path). Add:

    ```python
    # Load user skills for prompt-level awareness (separate from disk materialization)
    from pilot_space.infrastructure.database.repositories.user_skill_repository import (
        UserSkillRepository,
    )
    _user_skill_repo = UserSkillRepository(db_session)
    _active_skills = await _user_skill_repo.get_active_by_user_workspace(
        context.user_id, context.workspace_id,
    )
    _user_skills_for_prompt: list[dict[str, str]] = []
    for _s in _active_skills:
        _skill_display_name = _s.skill_name or (
            _s.template.name if _s.template else str(_s.id)[:8]
        )
        # Build a short description from skill_name + template name
        _desc = ""
        if _s.template:
            _desc = f"Personalized {_s.template.name} skill"
        elif _s.experience_description:
            # Truncate long descriptions to first 120 chars
            _desc = _s.experience_description[:120]
        _user_skills_for_prompt.append({"name": _skill_display_name, "description": _desc})
    ```

    Then update the `PromptLayerConfig` construction (lines 341-349) to pass `user_skills=_user_skills_for_prompt`:
    ```python
    assembled = await assemble_system_prompt(
        PromptLayerConfig(
            role_type=_role_type,
            workspace_name=input_data.context.get("workspace_name"),
            project_names=input_data.context.get("project_names"),
            user_message=input_data.message,
            has_note_context="<note_context>" in input_data.message,
            graph_context=graph_context,
            user_skills=_user_skills_for_prompt,
        )
    )
    ```

    NOTE: `get_active_by_user_workspace` is a second DB query after `materialize_role_skills` already queried the same data internally. This is acceptable because:
    1. The materializer runs in a try/except with legacy fallback -- duplicating its internal data extraction would couple prompt assembly to materializer internals.
    2. The query is lightweight (indexed, returns small result set).
    3. Both queries share the same `db_session` and benefit from SQLAlchemy's identity map caching.
  </action>
  <verify>
    <automated>cd /Users/tindang/workspaces/tind-repo/pilot-space/backend && uv run pyright backend/src/pilot_space/ai/agents/pilotspace_agent.py 2>&1 | tail -10 && uv run ruff check backend/src/pilot_space/ai/agents/pilotspace_agent.py 2>&1 | tail -10</automated>
  </verify>
  <done>
    - _build_stream_config loads active user skills from DB
    - Skill names and descriptions are formatted into list[dict[str, str]]
    - user_skills passed to PromptLayerConfig constructor
    - No type errors, no lint errors
  </done>
</task>

<task type="auto">
  <name>Task 3: Run full quality gates and verify integration</name>
  <files>
    backend/src/pilot_space/ai/prompt/models.py,
    backend/src/pilot_space/ai/prompt/prompt_assembler.py,
    backend/src/pilot_space/ai/agents/pilotspace_agent.py,
    backend/tests/unit/ai/prompt/test_prompt_assembler.py
  </files>
  <action>
    Run the full backend quality gate suite to catch any regressions:
    1. `cd backend && uv run ruff check` -- lint all changed files
    2. `cd backend && uv run pyright` -- type-check all changed files
    3. `cd backend && uv run pytest tests/unit/ai/ -x -v` -- run all AI unit tests

    Fix any issues found. If pyright reports type narrowing issues on `_s.template` access after the None check, add explicit `assert _s.template is not None` or use a conditional.
  </action>
  <verify>
    <automated>cd /Users/tindang/workspaces/tind-repo/pilot-space && make quality-gates-backend 2>&1 | tail -30</automated>
  </verify>
  <done>
    - ruff check passes with 0 errors
    - pyright passes with 0 errors on changed files
    - All AI unit tests pass
    - Coverage gate (80%) met
  </done>
</task>

</tasks>

<verification>
1. `cd backend && uv run pytest tests/unit/ai/prompt/test_prompt_assembler.py -x -v` -- all prompt tests pass including new TestSkillsLayer
2. `cd backend && uv run pyright src/pilot_space/ai/prompt/models.py src/pilot_space/ai/prompt/prompt_assembler.py src/pilot_space/ai/agents/pilotspace_agent.py` -- no type errors
3. `cd backend && uv run ruff check src/pilot_space/ai/prompt/ src/pilot_space/ai/agents/pilotspace_agent.py` -- no lint errors
4. `make quality-gates-backend` -- full quality gates pass
</verification>

<success_criteria>
- PromptLayerConfig has a `user_skills: list[dict[str, str]]` field
- `_build_skills_section()` formats skills into a "## Your Skills" prompt section
- `assemble_system_prompt()` includes skills section between workspace (layer 4) and session (layer 5)
- `_build_stream_config()` queries active user skills and passes them to `PromptLayerConfig`
- 4+ new tests in TestSkillsLayer all pass
- Existing prompt assembler tests still pass
- Full backend quality gates pass (ruff + pyright + pytest --cov >= 80%)
</success_criteria>

<output>
After completion, create `.planning/quick/260317-bch-check-change-of-feat-provider-setup-enha/260317-bch-01-SUMMARY.md`
</output>
