---
phase: 13-ai-provider-registry-model-selection
plan: "04"
subsystem: frontend/ai-chat
tags: [model-selector, mobx, localstorage, chat-ui, tdd]
dependency_graph:
  requires: [13-01, 13-03]
  provides: [ModelSelector component, PilotSpaceStore.selectedModel, model_override in sendMessage]
  affects: [ChatHeader, PilotSpaceActions.sendMessage, PilotSpaceStore]
tech_stack:
  added: []
  patterns: [TDD red-green, observer component, localStorage per-workspace persistence]
key_files:
  created:
    - frontend/src/features/ai/ChatView/ModelSelector.tsx
    - frontend/src/features/ai/ChatView/__tests__/ModelSelector.test.tsx
    - frontend/src/stores/ai/__tests__/PilotSpaceStore.model.test.ts
  modified:
    - frontend/src/features/ai/ChatView/ChatHeader.tsx
    - frontend/src/stores/ai/PilotSpaceStore.ts
    - frontend/src/stores/ai/PilotSpaceActions.ts
decisions:
  - ModelSelector returns null when availableModels is empty — no layout shift in ChatHeader
  - Per-workspace localStorage key chat_model_{workspaceId} — selection scoped to workspace, not global
  - setWorkspaceId calls loadSelectedModel automatically — no separate initialization required at call sites
  - model_override is undefined (not null) when no model selected — omitted from JSON body
  - onValueChange guards against is_selectable=false — redundant to disabled but prevents keyboard selection edge cases
metrics:
  duration: ~30 min
  completed_date: "2026-03-10"
  tasks_completed: 2
  files_changed: 6
requirements:
  - CHAT-01
  - CHAT-02
  - CHAT-03
---

# Phase 13 Plan 04: Chat Model Selector Summary

Per-session model picker in ChatHeader using shadcn Select, with localStorage persistence per workspace and model_override wiring to POST /ai/chat.

## Tasks Completed

| Task | Type | Description | Commit |
|------|------|-------------|--------|
| 1 | test (RED) | Wave-0 test scaffolds: ModelSelector + PilotSpaceStore.model | 2b287861 |
| 2 | feat (GREEN) | ModelSelector component + store extension + sendMessage wiring | f4427bc2 |

## What Was Built

**ModelSelector component** (`frontend/src/features/ai/ChatView/ModelSelector.tsx`):
- `observer` component reading `ai.settings.availableModels` from AISettingsStore
- shadcn `Select` dropdown renders all ProviderModelItem entries
- `is_selectable=false` items get `disabled` prop + `opacity-50 cursor-not-allowed` class
- `onValueChange` guard: skips non-selectable models before calling `setSelectedModel`
- Returns `null` when `availableModels.length === 0` (no layout shift)

**PilotSpaceStore extensions**:
- `selectedModel: { provider: string; modelId: string; configId: string } | null` observable
- `setSelectedModel(provider, modelId, configId)`: updates observable + persists to `chat_model_{workspaceId}`
- `loadSelectedModel(workspaceId)`: reads + validates localStorage entry; leaves null on missing/invalid/partial data
- `setWorkspaceId`: calls `loadSelectedModel` when workspaceId is non-null (auto-restore on workspace switch)

**ChatHeader update**:
- Spacer `<div className="flex-1 min-w-2">` now wraps `<ModelSelector />` centered in the gap

**PilotSpaceActions.sendMessage**:
- Added `model_override: { provider, model, config_id } | undefined` to POST /ai/chat body
- Undefined when `selectedModel` is null — backend ignores absent field, no behavior change for users without selection

## Deviations from Plan

None — plan executed exactly as written.

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| ModelSelector.test.tsx | 7 | PASS |
| PilotSpaceStore.model.test.ts | 10 | PASS |

**Key behaviors verified:**
- `availableModels=[]` → component renders null
- Selectable models render with display_name text
- Non-selectable models have `aria-disabled="true"` and `aria-selected="false"`
- `onValueChange` guard skips non-selectable models (logic test)
- `setSelectedModel` persists JSON to `chat_model_{wsId}` key
- `loadSelectedModel` restores from localStorage
- Invalid/partial JSON leaves `selectedModel` null without throwing
- Per-workspace isolation: switching `setWorkspaceId` restores correct model per workspace

## Self-Check

- [x] ModelSelector.tsx exists at expected path
- [x] PilotSpaceStore.ts has selectedModel, setSelectedModel, loadSelectedModel
- [x] ChatHeader.tsx imports and renders ModelSelector
- [x] PilotSpaceActions.ts has model_override in sendMessage body
- [x] Both test files pass (17/17)
- [x] Type-check clean
- [x] PilotSpaceStore.ts at 695 lines (under 700-line limit)
- [x] Commits 2b287861 and f4427bc2 exist
