# Feature Specification: Onboarding Launch Page

**Feature Number**: 010
**Branch**: `010-onboarding-launch`
**Created**: 2026-02-05
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: New users (all personas: Architect, Tech Lead, PM, Junior Dev) signing up for Pilot Space for the first time.

**Problem**: After creating an account, users land on an empty workspace home page with no guidance. They see template cards and a text input but have no understanding of the Note-First workflow, how to configure AI (BYOK keys), invite team members, or experience AI-augmented writing. The current home page (`/[workspaceSlug]`) shows hardcoded demo data (3 fake "recent notes") with no interactive onboarding flow. Users must discover Settings, AI Providers, and member invitation independently.

**Impact**: High abandonment risk within first 5 minutes. Users who don't configure AI keys never experience core value (ghost text, annotations, issue extraction). Teams that don't invite members miss collaboration features. Without guided first-note experience, users treat Pilot Space as a generic note app, missing the differentiating AI capabilities.

**Success**: A new workspace owner configures their Anthropic API key, invites at least one team member, and writes a guided note where they experience ghost text and AI annotations — all within a single session of 3 guided steps.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Product Owner / Architect | Conversion rate, time-to-value, Note-First adoption | Feature priorities, AI key flow decisions | Spec review |
| End User (New Signup) | First-time user | Quick setup, understanding value proposition | Usability feedback | Acceptance test |
| End User (Workspace Owner) | Admin inviting team | Team onboarding efficiency | Invitation flow feedback | Acceptance test |

---

## User Scenarios & Testing

### User Story 1 — Guided Workspace Setup (Priority: P1)

A workspace owner creates their first workspace. Instead of landing on an empty home page, they see a welcoming onboarding checklist that guides them through 3 essential setup steps: configuring the Anthropic AI key, inviting team members, and writing a guided first note. Each step is clearly explained with progress indication. The checklist is visible only to workspace owners and admins. It persists across sessions until all steps are completed or explicitly dismissed.

**Why this priority**: Without workspace setup, no AI features work (BYOK keys required per DD-002). This is the critical path to experiencing core product value. Users who skip AI configuration never see ghost text, annotations, or issue extraction.

**Independent Test**: Can be fully tested by creating a new account — delivers standalone guided setup capability that persists until completion.

**Acceptance Scenarios**:

1. **Given** a workspace owner has just created a new workspace, **When** they land on the workspace home page, **Then** they see an onboarding checklist with 3 steps (configure Anthropic AI key, invite members, write first note) showing 0/3 completion.
2. **Given** the onboarding checklist is visible, **When** the user clicks "Configure AI", **Then** they are navigated to the AI Providers settings page with contextual guidance explaining Anthropic key is required.
3. **Given** the user has completed 2 of 3 steps and closes the browser, **When** they return to the workspace home page, **Then** the checklist shows 2/3 completion with completed steps checked and remaining steps highlighted.
4. **Given** the user has completed all 3 steps, **When** they view the checklist, **Then** it shows a subtle animated checkmark with "All set!" message that auto-collapses after 3 seconds.
5. **Given** the user wants to skip onboarding, **When** they click "Skip for now" on the checklist, **Then** the checklist collapses to a minimal reminder in the sidebar that can be reopened.
6. **Given** a regular member (non-admin) joins an active workspace, **When** they land on the workspace home page, **Then** they see a simplified "Welcome" banner pointing to key features, not the full setup checklist.

---

### User Story 2 — Anthropic API Key Configuration with Validation (Priority: P1)

During onboarding, the user navigates to AI Providers settings to enter their Anthropic API key. The page explains the BYOK model, shows Anthropic as the single required provider, and validates the key via a separate backend endpoint that makes a lightweight authenticated request to Anthropic's API. After successful validation, the user sees which AI features are now unlocked. OpenAI remains visible as optional for future configuration.

**Why this priority**: The Anthropic key is the gateway to all core AI features (ghost text, PR review, issue extraction, annotations). Without a valid key, the entire AI layer is disabled. This must be frictionless.

**Independent Test**: Can be tested by navigating to AI Providers settings and entering an Anthropic API key — delivers standalone key validation capability.

**Acceptance Scenarios**:

1. **Given** the user is on the AI Providers settings page during onboarding, **When** they view the page, **Then** they see Anthropic as the required provider with a clear status indicator (not configured / validating / valid / invalid). OpenAI is shown as optional.
2. **Given** the user enters an Anthropic API key, **When** they click "Validate", **Then** a separate validation endpoint verifies the key with Anthropic's API (GET /v1/models) and shows success (green checkmark) or failure (red error with specific message).
3. **Given** the Anthropic key is validated, **When** the user views the provider summary, **Then** they see a feature unlock indicator showing available AI features (ghost text, code review, annotations, issue extraction, doc generation).
4. **Given** the user enters an invalid key, **When** validation fails, **Then** the error message specifies the issue (e.g., "Key format invalid", "Authentication failed — check your key at console.anthropic.com", "Insufficient permissions") with a help link to the Anthropic console.
5. **Given** the user has not configured any keys, **When** they try to use an AI feature (e.g., ghost text), **Then** they see a contextual prompt directing them to AI Providers settings.

---

### User Story 3 — Team Member Invitation (Priority: P2)

The onboarding checklist includes a step to invite team members. The user can enter email addresses with role assignments. Invited users receive a notification and can join the workspace. The invitation flow handles both existing Pilot Space users and new signups gracefully.

**Why this priority**: Collaboration is a core value proposition but not blocking individual user onboarding. A user can experience full value solo first, then invite team members.

**Independent Test**: Can be tested by opening the invite dialog and sending invitations — delivers standalone invitation capability.

**Acceptance Scenarios**:

1. **Given** the user clicks "Invite Members" from the onboarding checklist, **When** the invite dialog opens, **Then** they see an email input field, role selector (Admin/Member/Guest), and clear descriptions of each role's permissions.
2. **Given** the user enters a valid email and selects "Member" role, **When** they click "Send Invite", **Then** the invitation is created and the invitee appears in the pending invitations list.
3. **Given** the user invites an email that already has a Pilot Space account, **When** the invite is sent, **Then** that user is immediately added to the workspace (no pending state).
4. **Given** the user enters an invalid email format, **When** they attempt to send, **Then** inline validation shows "Please enter a valid email address" before the request is sent.
5. **Given** the user tries to invite an email already in the workspace, **When** they submit, **Then** they see "This person is already a member of this workspace" with no duplicate invitation created.

---

### User Story 4 — Guided First Note with AI Experience (Priority: P1)

The final onboarding step guides the user to write their first note with AI assistance. The system provides a pre-populated template with sample content about "Planning authentication for our app" that demonstrates ghost text, AI annotations, and issue extraction. The template includes action verbs (implement, fix, add) that trigger issue detection.

If AI keys are not configured, the user sees a soft warning banner in the editor but can still write and explore. AI-specific tooltips only appear when keys are valid. This is the "aha moment" — the user experiencing AI-augmented writing for the first time.

**Why this priority**: Without this guided experience, users may never discover ghost text (500ms pause trigger per DD-067) or margin annotations. The auth planning scenario is relatable to most dev teams and naturally generates extractable issues.

**Independent Test**: Can be tested by clicking "Write First Note" from the onboarding checklist — creates a sample note and guides the user through AI interactions.

**Acceptance Scenarios**:

1. **Given** the user clicks "Write Your First Note" from the onboarding checklist, **When** the note editor opens, **Then** it contains a starter template with 3-4 paragraphs about "Planning authentication for our app" with inline guidance callouts.
2. **Given** the user is in the guided note with Anthropic key configured, **When** they pause typing for 500ms, **Then** ghost text appears with a tooltip explaining "Press Tab to accept, Right Arrow for word-by-word, Escape to dismiss".
3. **Given** the note content triggers AI annotation detection, **When** annotations appear in the margin, **Then** a tooltip explains "AI detected potential issues — click to review".
4. **Given** the user has experienced ghost text and seen annotations, **When** they scroll to the bottom of the note, **Then** they see a "What's Next?" section with links to: create a project, explore issues board, configure GitHub integration.
5. **Given** the user completes the guided note experience, **When** they return to the workspace home page, **Then** the onboarding checklist shows 3/3 complete with a subtle animated checkmark.
6. **Given** the user opens the guided note WITHOUT AI keys configured, **When** the editor loads, **Then** a warning banner says "Configure your Anthropic API key to unlock AI writing assistance" with a direct link to settings. The note is still editable but ghost text and annotations are disabled.

---

### Edge Cases

- What happens when the user's browser has no internet connectivity during AI key validation? → Show "Unable to reach provider. Check your connection and try again." with retry button.
- What happens when the user dismisses onboarding then wants it back? → Sidebar "Getting Started" link always available in Settings until all steps complete.
- What happens when a workspace already has completed onboarding and a new member joins? → Onboarding checklist is visible only to owners/admins. Regular members see a simplified "Welcome" banner pointing to key features (FR-016).
- What happens when a new admin joins a workspace with incomplete onboarding? → They see the same checklist state as the owner (shared per-workspace state).
- What happens when AI keys expire or become invalid after initial setup? → AI Providers settings page shows "Key Invalid" status with re-validation prompt. Not part of onboarding scope.
- What happens when the guided note template is created but AI keys are not configured? → Ghost text and annotations are disabled. A prominent banner in the editor says "Configure AI keys to enable intelligent writing assistance" with a direct link.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display an onboarding checklist on the workspace home page for workspaces that have not completed setup, visible only to owners and admins, showing step-by-step progress (0/3 to 3/3)
- **FR-002**: System MUST persist onboarding completion state per workspace so that progress survives browser sessions
- **FR-003**: System MUST allow owners/admins to dismiss the onboarding checklist, collapsing it to a minimal sidebar reminder
- **FR-004**: System MUST navigate users to AI Providers settings when they click the "Configure AI" onboarding step
- **FR-005**: System MUST validate the Anthropic API key via a separate backend endpoint that makes a lightweight authenticated request to Anthropic's API (GET /v1/models)
- **FR-006**: System MUST display clear status for Anthropic provider: not configured, validating, valid, or invalid with specific error message
- **FR-007**: System MUST show which AI features become available after Anthropic key configuration (feature unlock summary)
- **FR-008**: System MUST provide an invitation dialog accessible from the onboarding checklist with email input and role selector
- **FR-009**: System MUST handle invitation of both existing users (immediate add) and new users (pending invitation)
- **FR-010**: System MUST prevent duplicate invitations to the same email within a workspace
- **FR-011**: System MUST create a guided note with starter template content ("Planning authentication for our app") when user clicks "Write First Note"
- **FR-012**: System MUST display contextual tooltips during the guided note experience explaining ghost text, annotations, and issue extraction — only when Anthropic key is configured
- **FR-013**: System MUST show a subtle celebration state (animated checkmark + "All set!" auto-collapsing after 3s) when all 3 onboarding steps are completed
- **FR-014**: System SHOULD display a "What's Next?" section after completing the guided note with links to key features
- **FR-015**: System SHOULD show a soft warning banner in the note editor when AI keys are not configured, with direct link to AI Providers settings
- **FR-016**: System SHOULD display a simplified welcome banner for non-admin members joining a workspace

### Key Entities

- **WorkspaceOnboarding**: Tracks onboarding progress per workspace. Key attributes: workspace_id, steps (3 booleans: ai_providers, invite_members, first_note), guided_note_id, dismissed_at, completed_at. Relationships: belongs to Workspace (1:1), references Note (guided note).
- **GuidedNote**: A regular Note created from an onboarding template with metadata flag. Key attributes: note_id, is_guided_template. Relationships: is a Note, referenced by WorkspaceOnboarding.

---

## Success Criteria

- **SC-001**: 80% of new workspace owners complete at least 2 of 3 onboarding steps within their first session
- **SC-002**: 90% of users who reach the AI Providers step successfully validate their Anthropic API key
- **SC-003**: Users complete the full onboarding flow (all 3 steps) in under 8 minutes
- **SC-004**: 70% of users who complete the guided note step continue to create at least one more note within 24 hours
- **SC-005**: Time from signup to first AI-augmented writing experience (ghost text) is under 5 minutes for users who follow the guided flow

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | Yes | Guided note demonstrates AI assistance with human control (Tab to accept, Escape to dismiss). Tooltips explain AI capabilities. |
| II. Note-First | Yes | Onboarding culminates in writing a note — reinforcing Note-First as the primary workflow. Home page remains note-centric. |
| III. Documentation-Third | No | N/A — onboarding is a UI feature, not documentation. |
| IV. Task-Centric | Yes | Each onboarding step is an independent, completable task with clear progress tracking. |
| V. Collaboration | Yes | Team invitation is an onboarding step. Workspace setup enables team collaboration from day one. |
| VI. Agile Integration | Yes | Stories decomposable into sprint-sized tasks. Each story delivers standalone value. |
| VII. Notation Standards | No | N/A — no diagram/notation needs. |

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
- [x] Functional requirements numbered sequentially (FR-001 to FR-016)
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
