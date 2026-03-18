# Feature Specification: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18
**Status**: Draft
**Input**: User description: "I want the admin workspace to be customizable with features via toggles. Please add settings for UI toggles (Notes, Issues, Projects, etc. from the sidebar), carefully add conditions to action references, and create a database table to apply to all users in the workspace."

---

## Problem Statement

Workspace administrators currently have no way to control which features are visible and accessible to their team. Every workspace shows the full set of sidebar modules (Notes, Issues, Projects, Members, Docs, Skills, Costs, Approvals) regardless of whether the team actually uses them. This creates a cluttered experience for teams that only need a subset of features, and prevents administrators from tailoring the workspace to their team's workflow.

## Goals

1. Allow workspace administrators to enable or disable sidebar feature modules for all members of the workspace.
2. Persist feature toggle configuration at the workspace level so it applies consistently to every user.
3. Conditionally hide disabled features from the sidebar navigation and restrict access to their routes.
4. Provide a dedicated settings page for managing feature toggles with immediate visual feedback.

## Non-Goals

- Per-user feature customization (this is workspace-wide only).
- Feature toggles for sub-features within a module (e.g., hiding specific issue views). This is module-level only.
- Billing/plan-based feature gating. Toggles are manual admin choices, not tied to subscription tiers.
- Disabling the "Home" module. Home is always visible as the workspace landing page.
- Disabling the "Settings" module. Settings must always be accessible to admins.

## Assumptions

- The existing `workspace.settings` JSONB column will be extended with a `feature_toggles` key to store module visibility state, following the same pattern as `ai_features`.
- Only Notes, Members, and Skill are enabled by default for new workspaces. Existing workspaces with no feature toggle configuration also use these defaults. Admins can enable additional features at any time.
- Only users with `owner` or `admin` roles can modify feature toggles.
- The "Home" and "Settings" navigation items are always visible and cannot be toggled off.
- Disabling a feature hides it from the sidebar and blocks navigation to its routes, but does not delete any underlying data.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Admin Configures Feature Visibility (Priority: P1)

A workspace administrator wants to simplify the sidebar for their team by disabling modules the team doesn't use (e.g., Docs, Costs). They navigate to Settings, find a "Features" settings page, and toggle off the unwanted modules. The changes take effect immediately for all workspace members.

**Why this priority**: This is the core capability — without the ability to toggle features, no other story works.

**Independent Test**: Navigate to Settings > Features as an admin, toggle off "Docs", verify sidebar no longer shows "Docs" for any workspace member.

**Acceptance Scenarios**:

1. **Given** an admin navigates to Settings > Features, **When** the page loads, **Then** they see a list of all toggleable features with switches showing current enabled/disabled state.
2. **Given** an admin toggles off "Docs", **When** the toggle is saved, **Then** the "Docs" item disappears from the sidebar for all workspace members (including the admin).
3. **Given** an admin toggles a feature back on, **When** the toggle is saved, **Then** the feature reappears in the sidebar and its route becomes accessible again.
4. **Given** a feature is toggled off, **When** a user directly navigates to that feature's URL (e.g., `/workspace-slug/docs`), **Then** they are redirected to the workspace home page.

---

### User Story 2 — Member Sees Only Enabled Features (Priority: P1)

A workspace member logs in and sees a sidebar that only contains the features the admin has enabled. They cannot see or access disabled features.

**Why this priority**: This validates that toggle changes propagate to all users, not just the admin.

**Independent Test**: As a non-admin member, verify the sidebar only shows features that the admin has enabled.

**Acceptance Scenarios**:

1. **Given** an admin has disabled "Projects" and "Costs", **When** a member views the sidebar, **Then** "Projects" and "Costs" are not visible.
2. **Given** a member bookmarked a now-disabled feature URL, **When** they navigate to that URL, **Then** they are redirected to the workspace home page.
3. **Given** a member is currently viewing a feature page and the admin disables that feature, **When** the member next navigates or refreshes, **Then** the disabled feature is no longer accessible.

---

### User Story 3 — Non-Admin Cannot Modify Feature Toggles (Priority: P2)

A regular member or guest attempts to access the Features settings page. They are either unable to see it in settings navigation or are denied access.

**Why this priority**: Ensures proper access control; secondary to the core toggle functionality.

**Independent Test**: Log in as a member-role user, verify the "Features" settings page is not visible or accessible.

**Acceptance Scenarios**:

1. **Given** a member-role user views the settings sidebar, **When** the page loads, **Then** the "Features" option is not visible in the settings navigation.
2. **Given** a member-role user tries to access the Features settings URL directly, **When** the request is made, **Then** they receive a forbidden error or are redirected.
3. **Given** a guest-role user, **When** they attempt to access the Features settings, **Then** they are denied access.

---

### User Story 4 — New Workspace Has Default Feature Set (Priority: P2)

When a new workspace is created, only the core features (Notes, Members, Skill) are enabled by default, providing a focused starting experience. Admins can enable additional features as needed.

**Why this priority**: Ensures a clean, focused onboarding experience while allowing full customization.

**Independent Test**: Create a new workspace, verify only Notes, Members, and Skill are visible in the sidebar.

**Acceptance Scenarios**:

1. **Given** a user creates a new workspace, **When** the workspace is initialized, **Then** only Notes, Members, and Skill are enabled; Issues, Projects, Docs, Costs, and Approvals are disabled.
2. **Given** an existing workspace that has never had feature toggles configured, **When** the Features settings page is loaded, **Then** toggles show the default state (Notes, Members, Skill on; others off).
3. **Given** an admin on a new workspace, **When** they visit Settings > Features, **Then** they can enable any disabled feature with a single toggle.

---

### User Story 5 — Feature Toggle Persists Across Sessions (Priority: P2)

An admin disables a feature, logs out, and logs back in. The feature remains disabled.

**Why this priority**: Validates persistence; basic requirement but not as high-priority as the core toggle flow.

**Independent Test**: Toggle off a feature, log out, log back in, verify the feature remains disabled.

**Acceptance Scenarios**:

1. **Given** an admin has disabled "Issues", **When** they log out and log back in, **Then** "Issues" is still not visible in the sidebar.
2. **Given** an admin has disabled "Issues", **When** a different admin logs in, **Then** they see the same disabled state for "Issues".

---

### User Story 6 — AI Skills and Tools Respect Feature Toggles (Priority: P1)

A workspace has "Issues" disabled. When a member uses the AI chat and asks "extract issues from my note", the AI agent does not execute the `extract-issues` skill. Instead, it informs the user that the Issues feature is not enabled and suggests contacting the admin.

**Why this priority**: Without this, the AI could create or manipulate data in disabled features, breaking the admin's intent and confusing users.

**Independent Test**: Disable "Issues" via feature toggles, open AI chat, request issue extraction, verify the agent refuses and explains the feature is disabled.

**Acceptance Scenarios**:

1. **Given** "Issues" is toggled off, **When** a user asks the AI to extract issues, **Then** the agent responds that the Issues feature is not enabled and does not execute the skill.
2. **Given** "Notes" is toggled off, **When** the AI agent lists available tools, **Then** note-related MCP tools (create note, search notes, etc.) are not present.
3. **Given** "Projects" is toggled off, **When** a user asks the AI to decompose tasks or plan a sprint, **Then** the agent responds that the Projects feature is not enabled.
4. **Given** a skill relates to multiple features (e.g., recommend-assignee for Issues and Members), **When** only one of those features is disabled, **Then** the skill remains available (it is only disabled when all related features are off).

---

## Functional Requirements *(mandatory)*

### FR-1: Feature Toggle Data Model

The system must store a set of feature toggles at the workspace level that control the visibility of sidebar modules. Each toggleable feature has a unique key and a boolean enabled/disabled state. The toggleable features are:

| Feature Key | Sidebar Item | Default  | Notes |
|-------------|-------------|----------|-------|
| `notes` | Notes | Enabled  | Note canvas module |
| `issues` | Issues | Disabled | Issue tracker module |
| `projects` | Projects | Disabled | Project management module |
| `members` | Members | Enabled  | Member directory module |
| `docs` | Docs | Disabled | Documentation module |
| `skills` | Skill | Enabled  | AI Skills module |
| `costs` | Costs | Disabled | AI cost tracking module |
| `approvals` | Approvals | Disabled | AI approval workflow module |

Non-toggleable (always visible): Home, Settings.

### FR-2: Feature Toggle Storage

The system must persist feature toggle settings at the workspace level in a way that:
- Applies to all users in the workspace uniformly.
- Defaults all features to their defined default state when no explicit configuration exists (Notes, Members, Skill enabled; others disabled).
- Supports atomic updates (toggling one feature does not affect others).

### FR-3: Admin Settings UI

The system must provide a "Features" page within workspace settings that:
- Displays all toggleable features as labeled switches with descriptions.
- Shows the current enabled/disabled state for each feature.
- Allows admins to toggle features on or off.
- Saves changes and provides visual confirmation of success.
- Is only accessible to users with `owner` or `admin` roles.

### FR-4: Sidebar Conditional Rendering

The sidebar navigation must conditionally render items based on the workspace feature toggle state:
- Items for disabled features are hidden from all users.
- The section labels ("Main", "AI") hide when all items within them are disabled.
- Pinned notes section behavior is unaffected (always shown when the sidebar is expanded, regardless of the "notes" toggle — pinned notes are a cross-cutting shortcut).

### FR-5: Route Protection

When a feature is disabled:
- Direct URL navigation to that feature's routes must redirect the user to the workspace home page.
- The redirect must be graceful with no error messages (the feature simply doesn't exist from the user's perspective).

### FR-6: API Access Control

The backend API must:
- Provide an endpoint for reading feature toggle state (accessible to all authenticated workspace members).
- Provide an endpoint for updating feature toggle state (restricted to `owner` and `admin` roles).
- Return appropriate error responses when a non-admin attempts to update toggles.

### FR-7: Feature Toggle Propagation

When an admin changes a feature toggle:
- The change must be reflected in the sidebar on the admin's next page load or navigation.
- Other users must see the updated sidebar on their next page load or navigation.
- No real-time push is required; eventual consistency on next load is acceptable.

### FR-8: AI Skill and Tool Disablement

When a feature is toggled off, all AI built-in skills and MCP tools related to that feature must also be disabled. The AI agent must not offer, execute, or surface capabilities for disabled features. The mapping is:

| Feature Toggle | Affected Skills | Affected MCP Tools |
|---------------|----------------|-------------------|
| `notes` | summarize, create-note-from-chat, generate-digest, improve-writing | note_server (all), note_content_server (all), note_query_server (all), ownership_server (all) |
| `issues` | extract-issues, enhance-issue, find-duplicates, recommend-assignee | issue_server (all), issue_relation_server (all) |
| `projects` | decompose-tasks, generate-pm-blocks, speckit-pm-guide, sprint-planning | project_server (all) |
| `docs` | generate-diagram, adr-lite, generate-code | (none) |
| `members` | recommend-assignee | (none) |
| `costs` | (none) | (none — cost tracking is infrastructure-level) |
| `approvals` | (none) | (none — approval workflow is infrastructure-level) |

Behavior when a disabled skill or tool is invoked:
- The AI agent must not list disabled skills in its available capabilities.
- If a user explicitly requests a disabled skill via chat, the agent must respond with a message explaining the feature is not enabled for this workspace and suggest the admin enable it in Settings > Features.
- MCP tools for disabled features must not appear in the agent's tool registry for that workspace session.
- Skills that span multiple features (e.g., `recommend-assignee` relates to both Issues and Members) are disabled only when **all** related features are toggled off.

---

## Key Entities *(optional — include when data model is involved)*

### WorkspaceFeatureToggles

Represents the set of enabled/disabled features for a workspace.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `notes` | Boolean | Yes | Whether the Notes module is enabled |
| `issues` | Boolean | Yes | Whether the Issues module is enabled |
| `projects` | Boolean | Yes | Whether the Projects module is enabled |
| `members` | Boolean | Yes | Whether the Members module is enabled |
| `docs` | Boolean | Yes | Whether the Docs module is enabled |
| `skills` | Boolean | Yes | Whether the Skills module is enabled |
| `costs` | Boolean | Yes | Whether the Costs module is enabled |
| `approvals` | Boolean | Yes | Whether the Approvals module is enabled |

---

## Success Criteria *(mandatory)*

1. **Admin configuration time**: An admin can enable or disable any feature in under 10 seconds from the Features settings page.
2. **Full sidebar customization**: All 8 toggleable features can be independently controlled without affecting each other.
3. **Workspace-wide consistency**: When a feature is disabled, 100% of workspace members see the same reduced sidebar on their next page load.
4. **Sensible defaults**: New workspaces start with only Notes, Members, and Skill enabled, providing a focused experience. Existing workspaces without toggle configuration use the same defaults.
5. **Access control enforcement**: Non-admin users cannot modify feature toggles, verified by both UI restriction and server-side enforcement.
6. **Route protection**: Users cannot access disabled feature pages via direct URL — they are redirected to the workspace home.
7. **Data preservation**: Disabling a feature does not delete or modify any existing data within that feature module. Re-enabling restores full access to all prior data.
8. **AI capability alignment**: When a feature is disabled, 100% of related AI skills and MCP tools are unavailable to the agent. The agent provides a clear explanation when a user requests a disabled capability.

---

## Dependencies

- Existing `workspace.settings` JSONB column for toggle storage (follows AI feature toggles pattern).
- Existing role-based access control (owner/admin/member/guest) for settings page visibility.
- Frontend sidebar component (`sidebar.tsx`) for conditional rendering.
- Frontend settings layout for adding the new "Features" page.
- AI skill discovery and MCP tool registry for filtering skills/tools by feature toggle state.
