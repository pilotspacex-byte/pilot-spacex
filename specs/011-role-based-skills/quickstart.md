# Quickstart Validation: Role-Based Skills

**Feature**: 011-role-based-skills
**Created**: 2026-02-06

---

## Scenario 1: Complete Onboarding with Role Setup (Happy Path)

**Prerequisites**: Test user account, empty workspace.

1. Login as test user → navigate to workspace home
2. Onboarding checklist shows 4 steps (0/4): Configure AI, Invite Members, Set Up Role, Write First Note
3. Complete "Configure AI" step (Anthropic key)
4. Click "Set Up Your Role" step
5. Role selection grid shows 8 predefined roles + "Custom Role" option
6. Select "Developer" → card highlights with checkmark
7. Click "Continue to Skill Setup"
8. Three options shown: "Use Default", "Describe Your Expertise", "Show Examples"
9. Click "Describe Your Expertise"
10. Type: "Full-stack engineer with 5 years experience. TypeScript, React, Node.js, PostgreSQL. Strong focus on clean architecture and testing."
11. Click "Generate Skill"
12. Wait for AI generation (loading spinner, <30s)
13. Preview shows auto-generated role name (e.g., "Senior Full-Stack TypeScript Developer") in an editable field above the skill content
14. **Verify**: Role name field is pre-filled and editable — user can change it
15. Click "Save & Activate"
16. **Verify**: Onboarding shows 2/4 complete (AI + Role)
17. **Verify**: Settings → Skills tab shows role card with the auto-generated (or user-edited) name and saved skill content
18. **Verify**: Word count shown below editor is within 2000 word limit

---

## Scenario 2: Agent Behavior Difference — Tester vs Developer

**Prerequisites**: Two users in same workspace. User A = Developer, User B = Tester.

### User A (Developer)

1. Login as User A (Developer role configured)
2. Open AI Chat → start new session
3. Send: "Help me plan the implementation of a user notification system"
4. **Verify**: Agent response focuses on:
   - Architecture patterns (pub/sub, event-driven)
   - Code structure and modules
   - Database schema suggestions
   - Implementation approach

### User B (Tester)

5. Login as User B (Tester role configured)
6. Open AI Chat → start new session
7. Send: "Help me plan the implementation of a user notification system"
8. **Verify**: Agent response focuses on:
   - Test scenarios and edge cases
   - Acceptance criteria
   - Performance testing considerations
   - Notification delivery verification

---

## Scenario 3: Skills Settings CRUD Operations

**Prerequisites**: User with "Developer" role configured.

### Edit

1. Navigate to Settings → Skills tab
2. "Developer" role card shown with skill content
3. Click "Edit" → editor opens with markdown content
4. Modify a focus area (e.g., add "GraphQL" to expertise)
5. Word counter updates in real-time
6. Click "Save"
7. **Verify**: Skill content updated, `updated_at` timestamp changed

### Add Secondary Role

8. Click "Add Role" button
9. Role grid shows (Developer already selected, grayed out)
10. Select "Architect" → proceed through skill generation
11. **Verify**: Skills tab now shows 2 cards: Developer (primary) + Architect (secondary)
12. **Verify**: "Developer" card has "Primary" badge

### Remove Role

13. Click "Remove" on "Architect" card
14. Confirmation dialog: "Remove Architect role? The associated skill will be deactivated."
15. Click "Confirm"
16. **Verify**: Skills tab shows only "Developer" card

### Reset to Default

17. Click "Reset to Default" on "Developer" card
18. Confirmation: "This will replace your custom skill with the default Developer template."
19. Confirm
20. **Verify**: Skill content reverts to default template text

---

## Scenario 4: Multi-Workspace Independence

**Prerequisites**: User is member of Workspace A and Workspace B.

1. In Workspace A: configure "Developer" role
2. In Workspace B: configure "Tester" role
3. Open AI Chat in Workspace A
4. Send: "Review this issue about adding caching"
5. **Verify**: Agent focuses on implementation, architecture patterns
6. Switch to Workspace B (sidebar workspace picker)
7. Open AI Chat in Workspace B
8. Send: "Review this issue about adding caching"
9. **Verify**: Agent focuses on test coverage, cache invalidation edge cases, performance benchmarks

---

## Scenario 5: Default Role + Owner Hint During Invitation

**Prerequisites**: User with "Developer" set as default role. Workspace owner inviting the user.

### Owner Side

1. Login as workspace owner → Settings → Members
2. Click "Invite Member"
3. Enter user's email, select "Member" role
4. "Suggest SDLC Role" dropdown appears → select "Tester"
5. Click "Send Invite"
6. **Verify**: Invitation created with suggested_sdlc_role = "Tester"

### Invitee Side

7. Login as invited user → accept invitation
8. Onboarding role selection step shows:
   - "Developer" highlighted with "Your default" label
   - "Tester" highlighted with "Suggested by workspace owner" label
9. **Verify**: Both suggestions visible, user can select either or choose differently

---

## Scenario 6: Error Handling — AI Generation Failure

**Prerequisites**: User at role skill generation step. AI provider temporarily unavailable.

1. Select "Developer" role in onboarding
2. Choose "Describe Your Expertise" and enter description
3. Click "Generate Skill"
4. AI provider returns error (simulated via invalid API key or circuit breaker)
5. **Verify**: Error notification: "Skill generation unavailable. Using default Developer template."
6. **Verify**: Default template skill content shown in preview
7. **Verify**: "Retry Generation" button available
8. User can accept default template and proceed

---

## Scenario 7: Edge Case — Maximum Roles Reached

**Prerequisites**: User with 3 roles already configured.

1. Navigate to Settings → Skills tab
2. 3 role cards displayed
3. Click "Add Role"
4. **Verify**: Warning message: "Maximum 3 roles per workspace. Remove an existing role to add a new one."
5. "Add Role" button disabled
6. Remove one role → "Add Role" button re-enables

---

## Scenario 8: Guest User Restriction

**Prerequisites**: User with "guest" workspace role.

1. Login as guest user → navigate to Settings
2. Skills tab visible but shows read-only view
3. **Verify**: No "Edit", "Add Role", or "Remove" buttons visible
4. **Verify**: Message: "Role skill configuration requires Member or higher access."
5. Attempt direct API call to POST /role-skills → returns 403
