# Tasks: Pilot Space Phase 2

**Source**: `/specs/002-pilot-space-phase2/`
**Required**: plan.md, spec.md (Phase 2), MVP complete
**Prerequisite**: All MVP (P0+P1) tasks must be complete

**Generated**: 2026-01-23 | **User Stories**: 9 | **Total Tasks**: 127

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label |

---

## Phase 9: User Story 5 - Organize Work with Modules/Epics (P2)

**Goal**: Enable epic/module grouping with progress tracking
**Verify**: Create module, link issues, see progress percentage update

### Database Models

- [ ] T216 [US5] Create Module SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/module.py`
- [ ] T217 [US5] Create migration for Module entity in `backend/alembic/versions/011_module_entity.py`

### Repositories

- [ ] T218 [US5] Create ModuleRepository in `backend/src/pilot_space/infrastructure/database/repositories/module_repository.py`

### Services

- [ ] T219 [US5] Create CreateModuleService in `backend/src/pilot_space/application/services/module/create_module_service.py`
- [ ] T220 [US5] Create GetModuleService in `backend/src/pilot_space/application/services/module/get_module_service.py` with progress computation

### API Endpoints

- [ ] T221 [US5] Create module schemas in `backend/src/pilot_space/api/v1/schemas/module.py`
- [ ] T222 [US5] Create modules router in `backend/src/pilot_space/api/v1/routers/modules.py`

### Frontend: Modules

- [ ] T223 [US5] Create ModuleStore MobX store in `frontend/src/stores/ModuleStore.ts`
- [ ] T224 [US5] Create ModuleList component in `frontend/src/components/modules/ModuleList.tsx`
- [ ] T225 [US5] Create ModuleDetail component in `frontend/src/components/modules/ModuleDetail.tsx`
- [ ] T226 [US5] Create ModuleProgressBar component in `frontend/src/components/modules/ModuleProgressBar.tsx`

### Frontend: Pages

- [ ] T227 [US5] Create modules list page in `frontend/src/app/(workspace)/projects/[projectId]/modules/page.tsx`
- [ ] T228 [US5] Create module detail page in `frontend/src/app/(workspace)/projects/[projectId]/modules/[moduleId]/page.tsx`

**Checkpoint**: US5 complete - Module/epic organization.

---

## Phase 10: User Story 6 - Create and Maintain Documentation Pages (P2)

**Goal**: Enable rich text documentation pages with AI generation
**Verify**: Create page, use rich text formatting, generate docs from code

### Database Models

- [ ] T229 [US6] Create Page SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/page.py`
- [ ] T230 [US6] Create migration for Page entity in `backend/alembic/versions/012_page_entity.py`

### Repositories

- [ ] T231 [US6] Create PageRepository in `backend/src/pilot_space/infrastructure/database/repositories/page_repository.py`

### AI Agents (US6)

- [ ] T232 [US6] Create DocGeneratorAgent in `backend/src/pilot_space/ai/agents/doc_generator_agent.py`
- [ ] T233 [US6] Create doc generation prompt template in `backend/src/pilot_space/ai/prompts/doc_generation.py`

### Services

- [ ] T234 [US6] Create CreatePageService in `backend/src/pilot_space/application/services/page/create_page_service.py`
- [ ] T235 [US6] Create GenerateDocService in `backend/src/pilot_space/application/services/ai/generate_doc_service.py`

### API Endpoints

- [ ] T236 [US6] Create page schemas in `backend/src/pilot_space/api/v1/schemas/page.py`
- [ ] T237 [US6] Create pages router in `backend/src/pilot_space/api/v1/routers/pages.py`
- [ ] T238 [US6] Add generate-docs endpoint to AI router

### Frontend: Pages (Documentation)

- [ ] T239 [US6] Create PageStore MobX store in `frontend/src/stores/PageStore.ts`
- [ ] T240 [US6] Create PageEditor component in `frontend/src/components/pages/PageEditor.tsx`
- [ ] T241 [US6] Create PageTree component in `frontend/src/components/pages/PageTree.tsx` for hierarchical navigation

### Frontend: Pages

- [ ] T242 [US6] Create pages list page in `frontend/src/app/(workspace)/projects/[projectId]/pages/page.tsx`
- [ ] T243 [US6] Create page detail page in `frontend/src/app/(workspace)/projects/[projectId]/pages/[pageId]/page.tsx`

**Checkpoint**: US6 complete - Documentation pages with AI generation.

---

## Phase 11: User Story 7 - Decompose Features into Tasks with AI (P2)

**Goal**: Enable AI task decomposition from feature descriptions with dependencies
**Verify**: Create feature issue, decompose into tasks, see dependencies marked

### AI Agents (US7)

- [ ] T244 [US7] Create TaskDecomposerAgent in `backend/src/pilot_space/ai/agents/task_decomposer_agent.py` using Claude Opus with tools
- [ ] T245 [US7] Create task decomposition prompt template in `backend/src/pilot_space/ai/prompts/task_decomposition.py`

### Services

- [ ] T246 [US7] Create DecomposeFeatureService in `backend/src/pilot_space/application/services/ai/decompose_feature_service.py`
- [ ] T247 [US7] Create CreateSubIssuesService in `backend/src/pilot_space/application/services/issue/create_sub_issues_service.py`

### Database Models

- [ ] T248 [US7] Create IssueLink SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/issue_link.py`
- [ ] T249 [US7] Create NoteIssueLink SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/note_issue_link.py`
- [ ] T250 [US7] Create migration for IssueLink and NoteIssueLink in `backend/alembic/versions/013_issue_links.py`

### API Endpoints

- [ ] T251 [US7] Create decomposition schemas in `backend/src/pilot_space/api/v1/schemas/decomposition.py`
- [ ] T252 [US7] Add decompose-task endpoint to AI router with SSE streaming

### Frontend: Task Decomposition

- [ ] T253 [US7] Create TaskDecompositionPanel component in `frontend/src/components/issues/TaskDecompositionPanel.tsx`
- [ ] T254 [US7] Create DependencyGraph component in `frontend/src/components/issues/DependencyGraph.tsx`
- [ ] T255 [US7] Create SubTaskList component in `frontend/src/components/issues/SubTaskList.tsx`

**Checkpoint**: US7 complete - AI task decomposition.

---

## Phase 12: User Story 8 - Generate Architecture Diagrams (P2)

**Goal**: Enable AI diagram generation from natural language
**Verify**: Describe diagram, generate Mermaid, edit code, insert into page

### AI Agents (US8)

- [ ] T256 [US8] Create DiagramGeneratorAgent in `backend/src/pilot_space/ai/agents/diagram_generator_agent.py`
- [ ] T257 [US8] Create diagram generation prompt template in `backend/src/pilot_space/ai/prompts/diagram_generation.py`

### API Endpoints

- [ ] T258 [US8] Create diagram schemas in `backend/src/pilot_space/api/v1/schemas/diagram.py`
- [ ] T259 [US8] Add generate-diagram endpoint to AI router

### Frontend: Diagram Generation

- [ ] T260 [US8] Create DiagramGenerator component in `frontend/src/components/ai/DiagramGenerator.tsx`
- [ ] T261 [US8] Create MermaidRenderer component in `frontend/src/components/ai/MermaidRenderer.tsx`
- [ ] T262 [US8] Create DiagramEditor component in `frontend/src/components/ai/DiagramEditor.tsx` with code + preview

**Checkpoint**: US8 complete - AI diagram generation.

---

## Phase 13: User Story 13 - Navigate with Command Palette and Search (P2)

**Goal**: Enable power user navigation with command palette, search, and keyboard shortcuts
**Verify**: Cmd+P opens palette, Cmd+K opens search, "/" opens slash commands

### Frontend: Command Palette & Search

- [ ] T263 [US13] Create CommandPalette component in `frontend/src/components/navigation/CommandPalette.tsx` with fuzzy search
- [ ] T264 [US13] Create SearchModal component in `frontend/src/components/navigation/SearchModal.tsx` with filters
- [ ] T265 [US13] Create FAB component in `frontend/src/components/navigation/FAB.tsx` (AI-enabled floating action button)
- [ ] T266 [US13] Create SlashCommandMenu component in `frontend/src/components/editor/SlashCommandMenu.tsx`
- [ ] T267 [US13] Create KeyboardShortcutOverlay component in `frontend/src/components/navigation/KeyboardShortcutOverlay.tsx`
- [ ] T268 [US13] Create useKeyboardShortcuts hook in `frontend/src/hooks/useKeyboardShortcuts.ts`
- [ ] T269 [US13] Create command registry in `frontend/src/lib/commands.ts`

**Checkpoint**: US13 complete - Command palette and navigation.

---

## Phase 14: User Story 14 - Explore Knowledge Graph (P2)

**Goal**: Enable relationship visualization with force-directed graph
**Verify**: Open graph, see connected nodes, pan/zoom, click to preview

### Database Models

- [ ] T270 [US14] Create KnowledgeGraphRelationship SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/knowledge_graph_relationship.py`
- [ ] T271 [US14] Create migration for KnowledgeGraphRelationship in `backend/alembic/versions/014_knowledge_graph.py`

### AI Agents (US14)

- [ ] T272 [US14] Create PatternDetectorAgent in `backend/src/pilot_space/ai/agents/pattern_detector_agent.py` for batch relationship detection

### Services

- [ ] T273 [US14] Create GetGraphDataService in `backend/src/pilot_space/application/services/graph/get_graph_data_service.py`
- [ ] T274 [US14] Create DetectPatternsService in `backend/src/pilot_space/application/services/ai/detect_patterns_service.py`

### API Endpoints

- [ ] T275 [US14] Create graph schemas in `backend/src/pilot_space/api/v1/schemas/graph.py`
- [ ] T276 [US14] Create graph router in `backend/src/pilot_space/api/v1/routers/graph.py`

### Frontend: Knowledge Graph

- [ ] T277 [US14] Create KnowledgeGraph component in `frontend/src/components/graph/KnowledgeGraph.tsx` using Sigma.js + react-sigma
- [ ] T278 [US14] Create GraphMinimap component in `frontend/src/components/graph/GraphMinimap.tsx`
- [ ] T279 [US14] Create NodePreview component in `frontend/src/components/graph/NodePreview.tsx`

### Frontend: Pages

- [ ] T280 [US14] Create graph page in `frontend/src/app/(workspace)/graph/page.tsx`

**Checkpoint**: US14 complete - Knowledge graph visualization.

---

## Phase 15: User Story 15 - Use Templates for New Notes (P2)

**Goal**: Enable quick note creation with templates and AI filling
**Verify**: Create note from template, see AI auto-fill hints

### AI Agents (US15)

- [ ] T281 [US15] Create TemplateFillerAgent in `backend/src/pilot_space/ai/agents/template_filler_agent.py`

### Frontend: Templates

- [ ] T282 [US15] Create NewNoteModal component in `frontend/src/components/notes/NewNoteModal.tsx` with template selection
- [ ] T283 [US15] Create TemplateGallery component in `frontend/src/components/notes/TemplateGallery.tsx`
- [ ] T284 [US15] Create TemplatePreview component in `frontend/src/components/notes/TemplatePreview.tsx`

**Checkpoint**: US15 complete - Template-based note creation.

---

## Phase 16: User Story 9 - Receive Notifications via Slack (P2)

**Goal**: Enable Slack notifications and /pilot command
**Verify**: Issue created → Slack notification, /pilot create works

### Slack Client

- [ ] T285 [US9] Create Slack API client in `backend/src/pilot_space/integrations/slack/client.py`
- [ ] T286 [US9] Create Slack command handler in `backend/src/pilot_space/integrations/slack/commands.py` for /pilot
- [ ] T287 [US9] Create Slack notification service in `backend/src/pilot_space/integrations/slack/notifications.py`

### Services

- [ ] T288 [US9] Create SendSlackNotificationService in `backend/src/pilot_space/application/services/notification/send_slack_notification_service.py`

### API Endpoints

- [ ] T289 [US9] Add Slack OAuth endpoints to integrations router
- [ ] T290 [US9] Add Slack webhook endpoint to webhooks router

### Frontend: Slack Integration

- [ ] T291 [US9] Create SlackIntegration component in `frontend/src/components/integrations/SlackIntegration.tsx`
- [ ] T292 [US9] Create NotificationPreferences component in `frontend/src/components/settings/NotificationPreferences.tsx`

**Checkpoint**: US9 complete - Slack notifications.

---

## Phase 17: User Story 17 - Receive AI-Prioritized Notifications (P2)

**Goal**: Enable AI-prioritized notification center
**Verify**: See notifications with AI priority labels, auto-mark as read

### AI Agents (US17)

- [ ] T293 [US17] Create NotificationPrioritizerAgent in `backend/src/pilot_space/ai/agents/notification_prioritizer_agent.py` using Gemini Flash

### Frontend: Notifications

- [ ] T294 [US17] Create NotificationCenter component in `frontend/src/components/notifications/NotificationCenter.tsx`
- [ ] T295 [US17] Create NotificationItem component in `frontend/src/components/notifications/NotificationItem.tsx` with priority badges
- [ ] T296 [US17] Create useNotifications hook in `frontend/src/features/notifications/hooks/useNotifications.ts`

**Checkpoint**: US17 complete - AI-prioritized notifications.

---

## Dependencies

### User Story Dependencies

| Story | Depends On | Can Run After |
|-------|------------|---------------|
| US5 | Foundation | MVP Complete |
| US6 | Foundation, US1 (TipTap) | MVP Complete |
| US7 | US2 (Issues) | MVP Complete |
| US8 | US6 (Pages) | T243 |
| US13 | US1, US2 | MVP Complete |
| US14 | US2, US6 | T243 |
| US15 | US1 (Notes) | MVP Complete |
| US9 | US2 (Issues) | MVP Complete |
| US17 | US2 (Issues) | MVP Complete |

### Parallel Opportunities

All Phase 2 stories can be worked on in parallel after MVP is complete, except:
- US8 (Diagrams) requires US6 (Pages) to be complete
- US14 (Knowledge Graph) requires US6 (Pages) to be complete

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 81 |
| US5 (Modules) | 13 |
| US6 (Documentation) | 15 |
| US7 (Task Decomposition) | 12 |
| US8 (Diagrams) | 7 |
| US13 (Command Palette) | 7 |
| US14 (Knowledge Graph) | 11 |
| US15 (Templates) | 4 |
| US9 (Slack) | 8 |
| US17 (Notifications) | 4 |

---

## Related Documentation

- [MVP Tasks](../001-pilot-space-mvp/tasks.md) - Foundation and P0+P1 tasks
- [Phase 3 Tasks](../003-pilot-space-phase3/tasks.md) - P3 discovery tasks
- [Phase 2 Spec](./spec.md) - User story specifications
- [Phase 2 Plan](./plan.md) - Implementation breakdown
