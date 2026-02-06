# Requirements Traceability: Onboarding Launch Page

## FR → User Story → Task Mapping

| FR ID | Requirement | User Story | Task(s) | Status |
|-------|-------------|-----------|---------|--------|
| FR-001 | Display onboarding checklist (owner/admin only, 3 steps) | US1 | T022, T024 | Pending |
| FR-002 | Persist onboarding state per workspace | US1 | T007, T008, T010, T011, T012, T016, T018 | Pending |
| FR-003 | Dismiss checklist (owner/admin) | US1 | T016, T022 | Pending |
| FR-004 | Navigate to AI Providers from checklist | US1 | T021, T022 | Pending |
| FR-005 | Validate Anthropic key via separate backend endpoint | US2 | T028, T029 | Pending |
| FR-006 | Display Anthropic provider status | US2 | T030, T032 | Pending |
| FR-007 | Show feature unlock summary (Anthropic features) | US2 | T031 | Pending |
| FR-008 | Invitation dialog from onboarding | US3 | T035, T036 | Pending |
| FR-009 | Handle existing vs new user invitations | US3 | (existing backend) | N/A |
| FR-010 | Prevent duplicate invitations | US3 | (existing backend) | N/A |
| FR-011 | Create guided note ("Planning auth for our app") with is_guided_template flag | US4 | T009, T040, T041, T042 | Pending |
| FR-012 | Contextual tooltips (only when Anthropic key configured) | US4 | T043, T046 | Pending |
| FR-013 | Subtle celebration (animated checkmark + "All set!" 3s) | US1 | T045, T022 | Pending |
| FR-014 | "What's Next?" section | US4 | T044 | Pending |
| FR-015 | Soft warning banner when AI keys not configured | US2/US4 | T033, T046 | Pending |
| FR-016 | Welcome banner for non-admin members | US1 | T023 | Pending |

## Infrastructure Tasks (Required for Database Persistence)

| Task | Description | Type |
|------|-------------|------|
| T006 | Create onboarding API client in frontend | API Client |
| T007 | Create WorkspaceOnboarding domain entity | Domain Layer |
| T008 | Create WorkspaceOnboarding SQLAlchemy model | Data Layer |
| T009 | Add is_guided_template column to Note model | Data Layer |
| T010 | Create Alembic migration (both tables + RLS) | Migration |
| T011 | Create OnboardingRepository | Repository |
| T012 | Create OnboardingService (CQRS-lite) | Service Layer |
| T017 | Register router + DI wiring | DI/Integration |
| T018 | Auto-create onboarding record on workspace creation | Integration |

## Clarification Decisions (from user review)

| Question | Decision | Impact |
|----------|----------|--------|
| Which providers required? | Anthropic only (OpenAI optional) | Simplified onboarding, single key validation |
| How many steps? | 3 steps (dropped "Workspace Profile" — already done at signup) | Faster completion, clearer flow |
| Step ordering enforcement? | Soft enforce — warn if AI keys not configured during guided note | Users can explore freely but see clear guidance |
| Key validation architecture? | Separate validate endpoint (POST /validate) | Validate before commit, existing save unchanged |
| Celebration style? | Subtle — animated checkmark + "All set!" auto-collapse 3s | Respects prefers-reduced-motion, non-intrusive |
| Checklist visibility? | Owner/Admin only | Regular members see welcome banner (FR-016) |
| Guided note template topic? | "Planning authentication for our app" | Realistic for dev teams, good issue extraction triggers |

## Design Decision References

| DD ID | Decision | How Used |
|-------|----------|----------|
| DD-002 | BYOK + Claude SDK | Anthropic key validation (single required provider for onboarding) |
| DD-013 | Note-First workflow | Onboarding culminates in guided note experience |
| DD-045 | Onboarding: Sample project | Guided note serves as lightweight sample content (full sample project deferred to Phase 3 US-16) |
| DD-060 | Supabase Platform | Vault for key encryption, RLS for onboarding table isolation |
| DD-061 | Auth + RLS | Onboarding endpoints enforce admin/owner role via RLS |
| DD-064 | CQRS-lite + Service Classes | OnboardingService follows Service.execute(Payload) pattern |
| DD-065 | MobX + TanStack Query | OnboardingStore (UI), useOnboardingState (server data) |
| DD-067 | Ghost text 500ms trigger | Guided note demonstrates ghost text with tooltip explanation |

## Integration Points

| Component | Integrates With | Task |
|-----------|----------------|------|
| WorkspaceService | OnboardingService (auto-create) | T018 |
| NoteService | OnboardingService (guided note creation) | T041 |
| InviteMemberDialog | useOnboardingActions (step completion) | T035 |
| ProviderStatusCard | onboardingApi (validation) | T030 |
| NoteEditor | GuidedNoteTooltips, AIKeyRequiredBanner | T046 |
| Workspace Home Page | OnboardingChecklist, WelcomeBanner | T024 |
