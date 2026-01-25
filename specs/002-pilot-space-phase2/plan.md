# Implementation Plan: Pilot Space Phase 2

**Branch**: `002-pilot-space-phase2` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Dependency**: Requires completion of `001-pilot-space-mvp`
**Scope**: P2 Features - Enhanced Productivity (9 User Stories)

## Summary

Phase 2 extends the Pilot Space MVP with enhanced productivity features. This phase builds on the stable foundation of P0+P1 features to add modules/epics, documentation pages, AI task decomposition, architecture diagrams, Slack integration, command palette navigation, knowledge graph, templates, and AI-prioritized notifications.

**Prerequisites**:
- MVP (001-pilot-space-mvp) must be complete and stable
- Core note canvas, issue management, sprint planning, GitHub integration, and AI Context features operational
- Supabase platform (Auth, Storage, Queues) fully configured

## Technical Context

**Inherits from MVP**: Python 3.12+ (Backend), TypeScript 5.x (Frontend), Supabase platform
**Additional Dependencies**:
- Sigma.js + @react-sigma/core (Knowledge Graph)
- Slack SDK (Integration)
- fuse.js (Command Palette fuzzy search)

## User Stories (9 Total)

| Priority | Story | Description | Dependencies |
|----------|-------|-------------|--------------|
| P2 | US-05 | Modules/Epics | US-02 (Issues) |
| P2 | US-06 | Documentation Pages | US-01 (TipTap) |
| P2 | US-07 | Task Decomposition | US-02 (Issues) |
| P2 | US-08 | Architecture Diagrams | US-06 (Pages) |
| P2 | US-09 | Slack Integration | US-02 (Issues) |
| P2 | US-13 | Command Palette | US-01, US-02 |
| P2 | US-14 | Knowledge Graph | US-02, US-06 |
| P2 | US-15 | Templates | US-01 (Notes) |
| P2 | US-17 | Notifications | US-02 (Issues) |

---

## User Story Implementation Breakdown

### US-05: Modules/Epics (P2)

**Spec Reference**: User Story 5 | **Priority**: P2 | **Acceptance Scenarios**: 4

**Clarifications Applied**:
```toon
US05clarify[2]{question,answer,impact}:
  Should modules have target dates?,Optional target date with overdue warning badge,Nullable target_date conditional badge UI
  How to calculate module progress?,Hybrid (points if available count fallback),Progress computation logic
```

**Data Model Entities**: Module, Issue
**Key Components**: `ModuleList.tsx`, `ModuleProgress.tsx`, `ModuleDetail.tsx`

**Implementation Tasks**:
1. Create Module domain entity with progress calculation logic
2. Add Module repository with issue aggregation queries
3. Create Module API endpoints (CRUD + progress)
4. Build ModuleList component with progress bars
5. Build ModuleDetail view with linked issues
6. Add overdue warning badge for target dates

---

### US-06: Documentation Pages (P2)

**Spec Reference**: User Story 6 | **Priority**: P2 | **Acceptance Scenarios**: 7

**Clarifications Applied**:
```toon
US06clarify[3]{question,answer,impact}:
  Autosave timing?,1-2 seconds inactivity,1.5s debounce
  Code block features?,Syntax highlighting language selector line numbers copy button,Full TipTap CodeBlock extension
  Image insert methods?,Paste drag & drop upload button URL embed,4 handlers in editor
```

**Data Model Entities**: Page
**Key Components**: `PageEditor.tsx`, `CodeBlockExtension.ts`, `ImageUpload.tsx`

**Implementation Tasks**:
1. Create Page domain entity with hierarchical structure
2. Add Page repository with tree queries
3. Create Page API endpoints (CRUD + hierarchy)
4. Build PageEditor with full TipTap configuration
5. Implement CodeBlockExtension with syntax highlighting
6. Implement all 4 image insert methods
7. Add autosave with 1.5s debounce
8. Integrate DocumentGeneratorAgent for AI documentation

---

### US-07: Task Decomposition (P2)

**Spec Reference**: User Story 7 | **Priority**: P2 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US07clarify[1]{question,answer,impact}:
  What estimation unit?,Story points (Fibonacci: 1 2 3 5 8 13),Constrained input validation
```

**Data Model Entities**: Issue (parent_id for sub-tasks, estimate_points)
**Key Components**: `TaskDecompositionAgent`, `SubtaskList.tsx`, `DecompositionModal.tsx`

**Implementation Tasks**:
1. Add parent_id and estimate_points to Issue entity
2. Create TaskDecomposerAgent with Claude SDK
3. Build decomposition prompt with Fibonacci estimation
4. Create API endpoint for decomposition trigger
5. Build DecompositionModal with review/edit UI
6. Build SubtaskList with dependency visualization

---

### US-08: Architecture Diagrams (P2)

**Spec Reference**: User Story 8 | **Priority**: P2 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US08clarify[1]{question,answer,impact}:
  How to edit Mermaid diagrams?,Code editor + live preview side-by-side,Split-pane UI component
```

**Data Model Entities**: Page (content with diagram blocks)
**Key Components**: `DiagramEditor.tsx`, `MermaidPreview.tsx`, `DiagramGeneratorAgent`

**Implementation Tasks**:
1. Create DiagramGeneratorAgent with Mermaid output
2. Add diagram type selection (sequence, class, flowchart, ERD, C4)
3. Build DiagramEditor with split-pane code/preview
4. Implement MermaidPreview with live rendering
5. Create API endpoint for diagram generation
6. Add diagram insertion into Page content

---

### US-09: Slack Integration (P2)

**Spec Reference**: User Story 9 | **Priority**: P2 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US09clarify[1]{question,answer,impact}:
  How /pilot create works?,Open Slack modal with title description priority fields,Slack Block Kit modal
```

**Data Model Entities**: Integration, Issue
**Key Components**: Slack App (`/pilot` command handler), modal builder, notification service

**Implementation Tasks**:
1. Create Slack App with Bot and User tokens
2. Implement OAuth flow for workspace installation
3. Build `/pilot create` slash command with Block Kit modal
4. Implement event handler for issue creation from Slack
5. Build notification posting service
6. Implement link unfurling
7. Create notification preferences management

---

### US-13: Command Palette (P2)

**Spec Reference**: User Story 13 | **Priority**: P2 | **Acceptance Scenarios**: 12

**UI Design References**: ui-design-spec.md Section 9
- Command Palette (Cmd+P): Section 9.1 (560px width, 70vh max-height, AI suggestions first)
- Search Modal (Cmd+K): Section 9.2 (full-page spotlight, content type filters)
- FAB: Section 8.7 (56px diameter, bottom-right, primary color)
- AI Panel: Section 8.6 (thin bar collapsed, pulse dot indicator)

**Clarifications Applied**:
```toon
US13clarify[1]{question,answer,impact}:
  Should AI suggestions learn from behavior?,Context-only ranking (no frequency learning),No ML model context-based scoring
```

**Component Mapping**:
```toon
US13components[6]{component,uiSpec,specs}:
  CommandPalette.tsx,9.1,560px width frosted glass AI suggestions section
  SearchModal.tsx,9.2,Full-page content filters (All/Notes/Issues/Projects)
  FAB.tsx,8.7,56px fixed bottom-right (24px margin) primary color
  CollapsibleAIPanel.tsx,8.6,Thin bar + pulse dot collapsed action chips expanded
  KeyboardShortcutGuide.tsx,9.3,? key trigger overlay with all shortcuts
  SlashCommandMenu.tsx,-,/ trigger in editor AI actions + formatting
```

**Implementation Tasks**:
1. Build CommandPalette with fuse.js fuzzy search
2. Implement AI suggestion service (context-based)
3. Build SearchModal with content type filters
4. Implement FAB component with AI search trigger
5. Build CollapsibleAIPanel with action chips
6. Implement slash command extension for TipTap
7. Build keyboard shortcut guide overlay
8. Add block move shortcuts (Cmd+Shift+Up/Down)
9. Implement progressive tooltips

---

### US-14: Knowledge Graph (P2)

**Spec Reference**: User Story 14 | **Priority**: P2 | **Acceptance Scenarios**: 7

**UI Design References**: Sigma.js + react-sigma
- Graph Visualization: WebGL, ForceAtlas2 layout
- Node Preview: Click shows note summary with AI analysis
- Mini-map: Shows current viewport position

**Clarifications Applied**:
```toon
US14clarify[5]{question,answer,impact}:
  Should graph preserve user positions?,Always auto-layout with ForceAtlas2,No position persistence
  What relationship types?,Explicit + semantic + mentions,3 relationship types
  How to detect semantic relationships?,Embedding similarity (cosine > 0.7) + metadata,Threshold-based detection
  Where to store graph?,PostgreSQL adjacency table,KnowledgeGraphRelationship entity
  When to update relationships?,Explicit on save; semantic weekly via batch job,pg_cron schedule
```

**Component Mapping**:
```toon
US14components[4]{component,library,specs}:
  KnowledgeGraph.tsx,@react-sigma/core,WebGL rendering ForceAtlas2 layout
  GraphMinimap.tsx,@react-sigma/minimap,Viewport position indicator
  NodePreview.tsx,-,Note summary AI connection analysis
  ClusterLabel.tsx,-,Project-based grouping
```

**Data Model Entities**: KnowledgeGraphRelationship
**Key Components**: `KnowledgeGraph.tsx` (Sigma.js), graph data service

**Implementation Tasks**:
1. Create KnowledgeGraphRelationship entity
2. Build graph data aggregation service
3. Create API endpoint for graph data retrieval
4. Build KnowledgeGraph component with Sigma.js
5. Implement ForceAtlas2 layout algorithm
6. Add GraphMinimap for navigation
7. Build NodePreview with AI analysis
8. Create PatternMatcherAgent for orphan detection
9. Add weekly semantic relationship batch job

---

### US-15: Templates (P2)

**Spec Reference**: User Story 15 | **Priority**: P2 | **Acceptance Scenarios**: 8

**UI Design References**: ui-design-spec.md Section 8.1
- New Note AI Prompt Flow: AI greeting, recommended templates
- Split View: Conversation left, live preview right

**Clarifications Applied**:
```toon
US15clarify[2]{question,answer,impact}:
  Where to store AI-generated templates?,Workspace-level library for team reuse,Template entity at workspace scope
  What placeholder syntax?,Smart AI detection (no syntax),AI inference for fill-ins
```

**Component Mapping**:
```toon
US15components[4]{component,uiSpec,specs}:
  NewNotePrompt.tsx,8.1,AI greeting prompt input template cards
  TemplateGallery.tsx,8.1,System + user + AI-generated templates
  ConversationalFiller.tsx,8.1,Split view conversation + live preview
  SimilarNotes.tsx,10.8,Post-creation similar notes with guidance
```

**Data Model Entities**: Template, Note
**Key Components**: `TemplateGallery.tsx`, `ConversationalTemplateFiller.tsx`

**Implementation Tasks**:
1. Create Template entity with workspace scope
2. Seed system templates (Sprint Plan, Feature Spec, Bug Analysis)
3. Build TemplateGallery component
4. Build NewNotePrompt with AI greeting
5. Implement ConversationalFiller with split view
6. Add template creation from existing notes
7. Implement similar note detection with AI guidance

---

### US-17: Notifications (P2)

**Spec Reference**: User Story 17 | **Priority**: P2 | **Acceptance Scenarios**: 5

**UI Design References**: ui-design-spec.md Section 10.7
- Notification Center: Smart inbox, priority tags
- Priority Tags: Urgent (red), Important (amber), FYI (muted)

**Clarifications Applied**:
```toon
US17clarify[1]{question,answer,impact}:
  How to determine notification priority?,AI considers urgency (deadline) user assignment mention type,AI-based priority scoring
```

**Component Mapping**:
```toon
US17components[3]{component,uiSpec,specs}:
  NotificationCenter.tsx,10.7,Sidebar panel 3-5 notification preview
  NotificationItem.tsx,10.7,Priority tag timestamp unread background tint
  NotificationBadge.tsx,10.7,Count badge on bell icon
```

**Data Model Entities**: Notification (to be added)
**Key Components**: `NotificationCenter.tsx`, notification service

**Implementation Tasks**:
1. Create Notification entity with priority field
2. Build notification creation service
3. Implement AI priority scoring logic
4. Create notification API endpoints
5. Build NotificationCenter component
6. Add delayed mark-as-read (2-3 second viewing)
7. Implement notification preferences management
8. Add Supabase Realtime subscription for live updates

---

## Implementation Priority Order

Phase 2 features should be implemented in this order based on dependencies:

```toon
phase2order[9]{order,story,deps,deliverable}:
  1,US-05: Modules/Epics,US-02,Issue organization
  2,US-06: Documentation,US-01 (TipTap),Rich text pages
  3,US-07: Task Decomposition,US-02,AI task planning
  4,US-08: Architecture Diagrams,US-06,Mermaid generation
  5,US-13: Command Palette,US-01 US-02,Power user navigation
  6,US-14: Knowledge Graph,US-02 US-06,Relationship visualization
  7,US-15: Templates,US-01,Note quick-start
  8,US-17: Notifications,US-02,Activity awareness
  9,US-09: Slack Integration,US-02,Team notifications
```

---

## Risk Assessment

```toon
phase2risks[5]{risk,impact,likelihood,mitigation}:
  Sigma.js learning curve,Medium,Medium,Use @react-sigma/core for React integration
  Slack API changes,Low,Low,Pin SDK versions abstract Slack-specific code
  Template AI detection accuracy,Medium,Medium,Provide manual placeholder editing fallback
  Knowledge graph performance at scale,Medium,Low,Sigma.js WebGL handles 50K+ nodes
  Notification fatigue,Medium,Medium,AI prioritization + configurable triggers
```

---

## Related Documentation

- [MVP Specification](../001-pilot-space-mvp/spec.md) - Foundation features (P0 + P1)
- [MVP Plan](../001-pilot-space-mvp/plan.md) - Foundation implementation plan
- [Phase 3 Specification](../003-pilot-space-phase3/spec.md) - Discovery & Onboarding features
- [Architecture Docs](../../docs/architect/README.md) - Technical architecture
