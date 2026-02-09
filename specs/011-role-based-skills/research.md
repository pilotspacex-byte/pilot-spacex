# Research Decisions: Role-Based Skills

**Feature**: 011-role-based-skills
**Created**: 2026-02-06

---

## RD-001: How to Inject Role Skills into Claude Agent SDK

**Question**: How should role-based skills reach the agent during a conversation?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. System prompt concatenation | Append role skill text to `SYSTEM_PROMPT_BASE` in PilotSpaceAgent before creating SDK client | Simple, direct control over injection point | Breaks SDK skill auto-discovery pattern. Must manually manage prompt size. Not compatible with SDK skill metadata (name, description). |
| B. Filesystem materialization | Write SKILL.md files to sandbox `.claude/skills/role-{name}/` before session. SDK auto-discovers via `setting_sources=["project"]`. | Reuses existing SDK mechanism. No PilotSpaceAgent changes for loading. Follows DD-087 filesystem skill pattern. Skills get proper YAML frontmatter. | Requires file I/O before each session (~100ms). Files must be cleaned/refreshed. |
| C. Custom MCP tool | Create an MCP tool that serves role skill content when agent queries it | Lazy loading — only loaded when needed | Agent must actively call the tool. Not guaranteed to be invoked. Adds complexity to MCP server. |

### Decision: **(B) Filesystem materialization**

**Rationale**: The Claude Agent SDK already auto-discovers skills from `.claude/skills/` via the `setting_sources=["project"]` configuration in `configure_sdk_for_space()` (sandbox_config.py:449). Writing SKILL.md files to the user's space directory before each session is the lowest-friction integration — the SDK handles discovery, parsing YAML frontmatter, and injection into the agent context. No changes needed to the existing `_stream_with_space()` skill loading flow.

**Performance**: Writing 1-3 small text files (<15KB each) is <100ms. Acceptable overhead before a session that takes 5-30s.

**Traceability**: FR-006, FR-007, FR-014

---

## RD-002: Skill Content Storage Strategy

**Question**: Where should role skill content live as the source of truth?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Database only | Store in PostgreSQL, generate SKILL.md files on-the-fly per request | Single source of truth. RLS-protected. Queryable. | Must materialize to filesystem for SDK. No git versioning. |
| B. Filesystem only | Store as files in user's sandbox space | Direct SDK consumption. Can be git-versioned. | No RLS protection. Hard to query across users. Must manage file permissions. |
| C. DB + materialized filesystem | DB is source of truth. Files materialized to sandbox before each session. | Best of both: RLS protection, queryable, AND SDK-compatible. | Slight complexity of two-phase storage. |

### Decision: **(C) DB + materialized filesystem**

**Rationale**: The DB provides RLS-enforced multi-tenant isolation (DD-061) and queryability for the Settings UI (FR-009). The filesystem is required by Claude Agent SDK for skill auto-discovery. Materialization bridges both needs. The cost is minimal — a simple write operation before each session.

**Traceability**: FR-005, FR-014

---

## RD-003: Multiple Role Skills Handling

**Question**: When a user has 2-3 roles, how should their skills reach the agent?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Merge into single SKILL.md | Concatenate all role skills into one file with sections | Single file. Clear precedence via ordering. | Large file. Harder for agent to distinguish roles. Skill names conflict. |
| B. Separate SKILL.md per role | Each role gets its own directory: `role-developer/SKILL.md`, `role-tester/SKILL.md` | SDK loads each independently. Clean separation. Agent sees distinct skills. | Agent must reason about multiple skills. Could conflict. |
| C. Primary role only | Only inject the primary role's skill | Simplest. No conflicts. | Ignores secondary roles. User configured them for a reason. |

### Decision: **(B) Separate files per role**

**Rationale**: The SDK already handles loading multiple skills from `.claude/skills/`. Each role skill directory (`role-developer/`, `role-tester/`) is independent. The primary role's SKILL.md includes a `priority: primary` tag in frontmatter so the agent can distinguish when roles conflict. This preserves the user's intent of having multiple roles while giving the agent clear priority signals.

**Traceability**: FR-002, FR-007

---

## RD-004: Onboarding Integration Point

**Question**: Where in the onboarding flow should role selection appear?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. New step (4th step) | Add `role_setup` as step 4 after `first_note` | Clean separation. Follows existing atomic step pattern. | Makes onboarding longer (4 steps vs 3). |
| B. Inline in invite_members | Add role selector to the invitation step | Fewer steps. Role relates to team composition. | Overloads the invite step. Role is personal, not team-level. |
| C. Post-onboarding prompt | After completing 3 steps, show a separate role setup modal | Doesn't change existing onboarding. Optional feel. | Users may dismiss and never configure. Loses the guided moment. |

### Decision: **(A) New step**

**Rationale**: The existing onboarding steps are atomic and independent (ai_providers, invite_members, first_note). Adding `role_setup` as a 4th step follows this pattern. The JSONB `steps` field is flexible — adding a new key requires no schema migration. Onboarding completion calculation updates from 3 to 4 steps. The role setup step is optional (skippable) to avoid blocking users who want to configure later.

**Traceability**: FR-001

---

## RD-005: AI Generation Model Selection

**Question**: Which model should generate role skill descriptions?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Claude Sonnet | Default orchestrator model | Good writing quality. Moderate cost. | Not the fastest option. |
| B. Claude Haiku | Fast, cheap | <5s response time. Lowest cost. | Writing quality may not match Sonnet for nuanced skill descriptions. |
| C. Gemini Flash | Fastest, cheapest | Sub-second for short outputs. | Different API. May not capture SKILL.md format nuances as well as Claude. |

### Decision: **(A) Claude Sonnet**

**Rationale**: Role skill descriptions are critical — they shape all future agent interactions. Quality matters more than speed here (one-time generation, not real-time). Sonnet provides the best quality-to-cost ratio for this use case. Uses the existing one-shot `query()` pattern (DD-011 provider routing for content enhancement). Generation is not latency-critical (<30s acceptable per SC-003).

**Traceability**: FR-003

---

## RD-006: Role Template Storage

**Question**: Where should predefined role templates live?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Hardcoded in Python | Templates as Python constants or config | Simple. No DB dependency. | Not versionable independently. Hard to update without deploy. |
| B. DB seed table | `role_templates` table populated by migration | Versionable (version field for FR-017). Admin-mutable in future. Queryable. | Requires migration. Must seed data. |
| C. YAML files in repo | Templates as YAML files in `ai/templates/` | Version-controlled. Easy to edit. | Not queryable. Must load from filesystem for API responses. |

### Decision: **(B) DB seed table**

**Rationale**: DB storage enables FR-017 (template update notifications) via a `version` field. When templates are updated in a future migration, the version increments, and the GET endpoint can compare with `user_role_skills.template_version` to notify users. The seed data is created in migration 024 alongside the table creation.

However, the initial template *content* (SKILL.md text) is authored as markdown files in `ai/templates/role_templates/` for easy editing, then read and inserted by the migration.

**Traceability**: FR-001, FR-017

---

## RD-007: SkillRegistry Revival

**Question**: Should we revive the removed SkillRegistry class for dynamic skill management?

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Revive SkillRegistry | Re-implement SkillRegistry with dynamic load/register methods | Programmatic control over skill loading. Can filter skills per user. | Was deliberately removed in 005-conversational-agent-arch. Adds complexity. |
| B. Keep filesystem auto-discovery | Continue using SDK's native `.claude/skills/` discovery | No code changes to agent loading. Proven pattern. Matches DD-087. | Less programmatic control. Must manage files. |

### Decision: **(B) Keep filesystem auto-discovery**

**Rationale**: SkillRegistry was intentionally removed (see `dependencies/ai.py:458` and `container.py:265`). The SDK's filesystem-based skill loading via `setting_sources=["project"]` is the established pattern. Materializing role skill files to the space directory before each session achieves the same goal without resurrecting removed infrastructure. The `_skill_registry` parameter in PilotSpaceAgent.__init__ already accepts None.

**Traceability**: Architecture consistency, DD-087
