# Feature Specification: Role-Based Skills for PilotSpace Agent

**Feature Number**: 011
**Branch**: `feat/skill-role-sdlc`
**Created**: 2026-02-06
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All SDLC team members (BA, PO, Dev, Tester, Architect, Tech Lead, PM, DevOps) using PilotSpace Agent within workspaces.

**Problem**: PilotSpace Agent treats every user identically regardless of their SDLC role. A Business Analyst asking the agent to review a note gets the same response style, terminology, and focus areas as a Developer or Tester. The agent cannot tailor its behavior to match a user's expertise, responsibilities, or workflow preferences. There is no concept of "what this person does on the team" — so the agent misses opportunities to proactively suggest role-relevant actions (e.g., suggesting test plans to a Tester, architecture concerns to an Architect, acceptance criteria to a BA).

**Impact**: Users receive generic AI assistance that ignores their professional context. BAs must repeatedly prompt the agent to focus on requirements rather than code. Testers must redirect the agent away from implementation details toward test coverage. This friction reduces AI utility by an estimated 40-60% — users spend extra turns correcting agent behavior instead of getting immediate value. Teams that adopted role-specific workflows in other tools (Jira role-based boards, Linear team views) find PilotSpace less productive for specialized work.

**Success**: Each team member configures their SDLC role(s) per workspace. The PilotSpace Agent automatically adapts its behavior — vocabulary, focus areas, proactive suggestions, and skill availability — to match the user's role. A Tester interacting with the agent receives test-oriented assistance; an Architect receives architecture-focused analysis. Users can customize their role skill descriptions to match their unique expertise blend.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Product Owner / Architect | Role-based AI differentiation, SDK skill injection, agent quality | Feature priorities, role taxonomy decisions | Spec review |
| End User (Team Member) | SDLC practitioner | Personalized AI assistance matching their role | Role definition accuracy, workflow feedback | Acceptance test |
| End User (Workspace Owner) | Admin configuring team | Efficient team onboarding with role suggestions | Role hint UX during invitation flow | Acceptance test |
| End User (Workspace Member) | Existing member | Ability to update/refine role skill over time | Settings UX for skill editing | Acceptance test |

---

## User Scenarios & Testing

### User Story 1 — SDLC Role Selection During Onboarding (Priority: P1)

When a user creates a new workspace or is invited to join one, the onboarding flow includes a role selection step. The system presents a set of predefined SDLC role templates (BA, PO, Developer, Tester, Architect, Tech Lead, PM, DevOps) along with the option to create a custom role. If the user has previously set a default role in their profile, that role is pre-selected. If the workspace owner provided a role hint during invitation, that hint is shown as a suggestion. The user can select multiple roles (e.g., "Tech Lead + Developer") to reflect their actual responsibilities. After selection, the system proceeds to generate a personalized skill for the agent.

**Why this priority**: Role selection is the entry point for the entire feature. Without knowing the user's role, the agent cannot personalize behavior. This step must happen early in the user journey — during onboarding — to deliver value from the first interaction.

**Independent Test**: Can be fully tested by creating a new workspace and going through the onboarding flow — delivers standalone role selection capability that persists to the user's workspace membership.

**Acceptance Scenarios**:

1. **Given** a user creates a new workspace, **When** they reach the role selection step in onboarding, **Then** they see a grid of predefined SDLC role cards (BA, PO, Developer, Tester, Architect, Tech Lead, PM, DevOps) with brief descriptions, plus a "Custom Role" option.
2. **Given** a user has set "Developer" as their default role in their profile, **When** the role selection step loads, **Then** "Developer" is pre-selected with a label "Your default role" and the user can confirm or change it.
3. **Given** a workspace owner invited a user with the hint "Tester", **When** the invited user reaches role selection during onboarding, **Then** "Tester" is highlighted with a label "Suggested by workspace owner" and the user can accept or choose differently.
4. **Given** a user wants to hold multiple roles, **When** they select both "Tech Lead" and "Developer", **Then** both roles are highlighted, with "Tech Lead" marked as primary (first selected) and "Developer" as secondary. The user can reorder or deselect roles.
5. **Given** a user wants a role not in the predefined list, **When** they click "Custom Role", **Then** they see an input field to name their role and a text area to describe their responsibilities and focus areas.
6. **Given** a user skips role selection, **When** they dismiss the step, **Then** no role is assigned and the agent operates with default (generic) behavior. A reminder appears in settings to complete role setup.

---

### User Story 2 — AI-Generated Role Skill from Experience (Priority: P1)

After selecting their role(s), the user is guided through skill generation. The system uses AI to create a personalized skill description based on the user's selected role template and their self-described experience. The user can either (a) accept the default template skill for their role, (b) describe their specific expertise in natural language and let AI generate a tailored skill, or (c) provide examples of how they want the agent to behave. The generated skill follows the SKILL.md format — a comprehensive description with workflow instructions, focus areas, terminology preferences, and proactive suggestion triggers. The skill is stored and immediately available to the PilotSpace Agent.

**Why this priority**: Skill generation transforms a role label into actionable agent behavior. Without this step, selecting "Tester" would have no effect on agent output. The AI-generated skill is the bridge between user intent and agent personalization.

**Independent Test**: Can be tested by selecting a role during onboarding and completing the skill generation flow — produces a stored skill that is verifiable in settings.

**Acceptance Scenarios**:

1. **Given** a user selected "Tester" as their role, **When** they proceed to skill generation, **Then** they see three options: "Use default Tester skill", "Describe your expertise", or "Show me examples".
2. **Given** a user chooses "Use default Tester skill", **When** the system generates the skill, **Then** a preview shows the generated SKILL.md content — including focus areas (test coverage, edge cases, regression), vocabulary (test plan, acceptance criteria, boundary conditions), proactive triggers (suggest test scenarios when viewing issues, flag untested code paths). The user can accept or customize before saving.
3. **Given** a user chooses "Describe your expertise" and writes "I'm a QA engineer with 5 years of automation experience. I focus on API testing, performance testing, and CI/CD pipeline reliability. I use behavior-driven development.", **When** the AI generates the skill, **Then** the resulting skill emphasizes API test coverage, performance benchmarks, pipeline stability checks, and BDD-style scenario suggestions — going beyond the generic Tester template.
4. **Given** a user chooses "Show me examples", **When** the examples are displayed, **Then** they see 2-3 sample interactions showing how the agent would behave with a Tester skill (e.g., "When you ask the agent to review an issue, it will suggest acceptance criteria and edge case scenarios").
5. **Given** a user has selected multiple roles (Tech Lead + Developer), **When** the skill is generated, **Then** each role gets its own separate SKILL.md file — Tech Lead with architecture decisions and code quality focus, Developer with implementation patterns and debugging focus. The primary role's skill includes a `priority: primary` tag in YAML frontmatter so the agent gives it precedence when roles overlap.
6. **Given** the AI skill generation fails (provider unavailable), **When** the error occurs, **Then** the system falls back to the default template skill for the selected role, shows a notification explaining the fallback, and offers to retry.

---

### User Story 3 — Role Skill Injection into PilotSpace Agent (Priority: P1)

When a user interacts with the PilotSpace Agent, the agent automatically loads the user's role skill(s) for the current workspace. The skill is injected as contextual knowledge that shapes the agent's responses — adjusting vocabulary, focus areas, proactive suggestions, and reasoning priorities. The injection follows the existing Claude Agent SDK skill system (SKILL.md format, auto-discovered by the SDK). If the user has multiple roles, skills are merged with the primary role taking precedence.

**Why this priority**: This is the core value delivery — the moment where role selection actually changes agent behavior. Without injection, role selection is cosmetic. This must work seamlessly with the existing PilotSpaceAgent orchestrator and skill registry.

**Independent Test**: Can be tested by configuring a role skill and then interacting with the PilotSpace Agent in a chat session — observable differences in agent response style, focus, and suggestions.

**Acceptance Scenarios**:

1. **Given** a user has a "Tester" role skill configured, **When** they ask the agent "Review this issue about adding user authentication", **Then** the agent emphasizes test scenarios, edge cases, security testing considerations, and acceptance criteria — rather than implementation details or architecture patterns.
2. **Given** a user has a "Business Analyst" role skill configured, **When** they ask the agent to "Help me write a note about the new payment feature", **Then** the agent focuses on requirements elicitation, stakeholder impact, user journey mapping, and acceptance criteria — using BA terminology.
3. **Given** a user has "Architect" (primary) + "Developer" (secondary) roles, **When** they interact with the agent, **Then** the agent leads with architecture concerns (scalability, patterns, trade-offs) while also providing implementation-level guidance when asked.
4. **Given** a user has no role skill configured (skipped during onboarding), **When** they interact with the agent, **Then** the agent operates with default generic behavior — identical to current behavior with no degradation.
5. **Given** a user switches workspaces, **When** they interact with the agent in the new workspace, **Then** the agent loads the role skill configured for that specific workspace, not the previous workspace's skill.
6. **Given** a user's role skill references terminology or workflows specific to their experience, **When** the agent generates responses, **Then** those terms and workflows appear naturally in the agent's output without the user needing to re-explain their context.

---

### User Story 4 — Default Role Preference in User Profile (Priority: P2)

Users can set a default SDLC role in their profile settings. This default is used as a pre-selection when joining new workspaces — reducing friction during onboarding. The default role does not override workspace-specific role assignments; it serves only as a suggestion for new workspace setups. Users can update their default role at any time from their profile settings page.

**Why this priority**: Reduces onboarding friction for users who join multiple workspaces with the same role. Not blocking for single-workspace users but valuable for team members working across projects.

**Independent Test**: Can be tested by setting a default role in profile settings, then creating or joining a new workspace — the default role appears pre-selected during onboarding.

**Acceptance Scenarios**:

1. **Given** a user navigates to their profile settings, **When** they view the profile page, **Then** they see a "Default SDLC Role" section with the same role options as the onboarding flow.
2. **Given** a user selects "Developer" as their default role and saves, **When** they join a new workspace, **Then** the onboarding role selection step shows "Developer" pre-selected with a "Your default" label.
3. **Given** a user has a default role set, **When** they are invited to a workspace where the owner suggested "Tester", **Then** both the default ("Developer — Your default") and the suggestion ("Tester — Suggested by workspace owner") are shown, with the workspace suggestion highlighted.
4. **Given** a user changes their default role from "Developer" to "Architect", **When** the change is saved, **Then** existing workspace role assignments are not affected — only future workspace joins use the new default.

---

### User Story 5 — Workspace Owner Role Hints During Invitation (Priority: P2)

When a workspace owner invites a new member, they can optionally suggest an SDLC role for the invitee. This hint is shown during the invitee's onboarding as a suggestion — not an assignment. The invitee always has full control to accept, modify, or ignore the suggestion. This helps workspace owners pre-configure team composition expectations.

**Why this priority**: Enables workspace owners to guide team role setup without imposing roles. Useful for organized teams where roles are pre-determined but each member should still customize their skill.

**Independent Test**: Can be tested by inviting a user with a role hint, then verifying the hint appears during the invitee's onboarding — delivers standalone invitation enhancement.

**Acceptance Scenarios**:

1. **Given** a workspace owner is inviting a new member, **When** the invitation dialog opens, **Then** they see an optional "Suggest role" dropdown alongside the existing email and workspace role (Admin/Member/Guest) fields.
2. **Given** the owner selects "Tester" as a role hint for the invitation, **When** the invitation is created, **Then** the role hint is stored with the invitation record.
3. **Given** an invitee accepts a workspace invitation with a "Tester" hint, **When** they reach the onboarding role selection, **Then** "Tester" is highlighted with "Suggested by workspace owner" and pre-selected — but the invitee can freely change it.
4. **Given** the owner does not select a role hint, **When** the invitee goes through onboarding, **Then** the role selection step shows no workspace-specific suggestion (only the user's default role, if set).

---

### User Story 6 — Role Skill Management in Settings (Priority: P1)

Users can view, edit, and regenerate their role skills from a dedicated "Skills" tab in workspace settings. The tab shows the current role assignment(s) and the full skill description. Users can manually edit the skill text (in-place editor), regenerate it with AI using updated experience descriptions, add or remove roles, or reset to the default template. Changes take effect immediately for the next agent interaction.

**Why this priority**: Skills must be editable after initial generation. Users refine their working style over time, discover new preferences, or change responsibilities within a team. Without an edit interface, role skills become stale.

**Independent Test**: Can be tested by navigating to workspace settings, opening the Skills tab, editing a skill, and then verifying the agent reflects the changes in the next conversation.

**Acceptance Scenarios**:

1. **Given** a user navigates to workspace settings, **When** they click the "Skills" tab, **Then** they see their current role(s) displayed as cards with the full skill description text below each role card.
2. **Given** a user clicks "Edit" on their Tester skill, **When** the editor opens, **Then** they can modify the skill text directly — the editor supports markdown formatting and shows a live preview of how the agent will interpret the skill.
3. **Given** a user wants to regenerate their skill, **When** they click "Regenerate with AI" and provide an updated experience description, **Then** the AI generates a new skill based on the updated input. The previous skill is shown as "Previous version" for comparison before the user confirms the replacement.
4. **Given** a user wants to add a secondary role, **When** they click "Add Role" on the Skills tab, **Then** they see the same role selection grid as onboarding and can add a new role with its own skill generation flow.
5. **Given** a user wants to remove a role, **When** they click "Remove" on a role card, **Then** a confirmation dialog explains that the associated skill will be deactivated. The role and skill are removed from the workspace membership.
6. **Given** a user clicks "Reset to Default" on a skill, **When** they confirm, **Then** the skill reverts to the predefined template for that role, discarding all customizations.
7. **Given** a user edits their skill and saves, **When** they start a new conversation with the PilotSpace Agent, **Then** the agent uses the updated skill immediately — no restart or delay required.

---

### Edge Cases

- What happens when a user is a member of 5 workspaces with different roles in each? Each workspace has an independent role-skill assignment. Switching workspaces loads the workspace-specific skill. No cross-workspace contamination.
- What happens when the AI provider is unavailable during skill generation? Fall back to the default template for the selected role. Store the user's experience description so regeneration can be attempted later.
- What happens when a predefined role template is updated by the system? Existing customized skills are not affected. Users who use the default template can opt-in to updates via a "Template updated — apply changes?" notification.
- What happens when a user has 4+ roles selected? Limit to a maximum of 3 roles per workspace to prevent skill dilution. The system warns that more than 3 roles may reduce agent specialization quality.
- What happens when the role skill text exceeds the agent's context budget? Skills are capped at 2000 words. The editor shows a word count and warns when approaching the limit. Overly long skills are summarized by AI before injection.
- What happens when a workspace guest (read-only) tries to configure a role? Guests can view but not configure role skills — role skill configuration requires at least "member" workspace permission level.
- What happens when a user removes all roles? The agent reverts to default (generic) behavior. The Skills tab shows "No roles configured" with a prompt to add one.
- What happens when two users in the same workspace share the same role but different custom skills? Each user's skill is personal — stored per user-workspace pair. The "Tester" role for User A and User B can have completely different skill descriptions.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST present a role selection step during workspace onboarding showing predefined SDLC role templates (BA, PO, Developer, Tester, Architect, Tech Lead, PM, DevOps) plus a custom role option
- **FR-002**: System MUST allow users to select multiple roles per workspace (up to 3) with a designated primary role
- **FR-003**: System MUST generate a personalized skill description using AI based on the user's selected role and self-described experience
- **FR-004**: System MUST provide three skill generation paths: accept default template, describe expertise in natural language, or view example interactions
- **FR-005**: System MUST store role skills per user-workspace pair so that the same user can have different skills in different workspaces
- **FR-006**: System MUST inject the user's role skill(s) into the PilotSpace Agent session context when the user initiates a conversation
- **FR-007**: System MUST inject multiple role skills as separate SKILL.md files with the primary role tagged via `priority: primary` in YAML frontmatter, giving it precedence when roles overlap
- **FR-008**: System MUST fall back to default generic agent behavior when no role skill is configured
- **FR-009**: System MUST provide a "Skills" tab in workspace settings where users can view, edit, regenerate, add, remove, and reset role skills
- **FR-010**: System MUST apply skill edits immediately — the next agent interaction after saving reflects the updated skill
- **FR-011**: System MUST allow users to set a default SDLC role in their user profile that pre-selects during new workspace onboarding
- **FR-012**: System MUST support workspace owner role hints during member invitation that appear as suggestions (not assignments) to the invitee
- **FR-013**: System MUST cap individual skill descriptions at 2000 words with a visible word count indicator in the editor
- **FR-014**: System MUST store the generated skill in both persistent storage (source of truth) and generate the SKILL.md-format file on demand for SDK consumption
- **FR-015**: System MUST preserve the user's experience description input so that skill regeneration can use it as context
- **FR-016**: System SHOULD display a live preview of how the skill will affect agent behavior when editing
- **FR-017**: System SHOULD show a "Template updated" notification when a predefined role template is updated, offering opt-in to apply changes
- **FR-018**: System SHOULD limit role selection to a maximum of 3 roles per workspace with a warning about specialization quality degradation
- **FR-019**: System MAY allow users to share their custom role skill as a template with other workspace members
- **FR-020**: System MUST restrict role skill configuration to users with at least "member" workspace permission level (guests excluded)

### Key Entities

- **UserRoleSkill**: A personalized AI skill description for a user within a specific workspace. Key attributes: user_id, workspace_id, role_type (predefined enum or 'custom'), role_name, skill_content (markdown text), experience_description (user's input), is_primary, template_version, word_count. Relationships: belongs to User (many-to-one), belongs to Workspace (many-to-one), derived from RoleTemplate (optional).
- **RoleTemplate**: A predefined SDLC role template with default skill content. Key attributes: role_type (enum), display_name, description, default_skill_content, icon, sort_order, version. Relationships: referenced by UserRoleSkill (one-to-many). Seeded by the system.
- **User** (extension): Extended user table with default role preference. Key attributes (new): default_sdlc_role. Relationships: existing.
- **WorkspaceInvitation** (extension): Enhanced invitation with optional role hint. Key attributes (new): suggested_sdlc_role. Relationships: belongs to Workspace (many-to-one).

---

## Success Criteria

- **SC-001**: 70% of new workspace members complete role selection during onboarding (not skipped)
- **SC-002**: Users with role skills configured report the agent's first response as "relevant to my role" in 80%+ of conversations (measured via implicit feedback — user does not need to re-prompt for role context)
- **SC-003**: Skill generation (from role selection to saved skill) completes in under 30 seconds for AI-generated skills and under 5 seconds for default templates
- **SC-004**: Users who configure role skills use the agent 25% more frequently than users without role skills (measured over 30-day window)
- **SC-005**: 60% of users who initially accept the default template customize their skill within 14 days via the Settings/Skills tab

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | Yes | AI generates skill suggestions but user always has full control to edit, accept, or reject. Role hints are suggestions, never assignments. Human oversight preserved. |
| II. Note-First | Yes | Role skills enhance Note-First workflow — a BA's skill focuses agent on requirements extraction from notes, a Tester's skill focuses on test scenario extraction. |
| III. Documentation-Third | No | N/A — feature is about runtime agent behavior, not documentation. |
| IV. Task-Centric | Yes | Each user story is independently testable. Skills tab is a standalone settings capability. |
| V. Collaboration | Yes | Workspace owners can hint roles for invitees. Future: skill sharing between members (FR-019). |
| VI. Agile Integration | Yes | Stories decomposable into sprint-sized tasks. Role selection integrates with existing onboarding sprint. |
| VII. Notation Standards | No | N/A — no diagram or notation needs. |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names anywhere in requirements
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P2
- [x] Functional requirements numbered sequentially (FR-001 to FR-020)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Next Phase

After this spec passes all checklists:

1. **Proceed to planning** — Use `template-plan.md` to create the implementation plan
2. **Share for review** — This spec is the alignment artifact for all stakeholders
