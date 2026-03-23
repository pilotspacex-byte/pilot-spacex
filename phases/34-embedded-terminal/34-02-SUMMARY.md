---
phase: 34-embedded-terminal
plan: 02
subsystem: ui
tags: [xterm.js, terminal, mobx, react, tauri, pty, typescript]

# Dependency graph
requires:
  - phase: 34-01
    provides: Rust PTY backend (portable-pty), Tauri IPC commands (create_terminal, write_terminal, resize_terminal, close_terminal), TypeScript typed wrappers in tauri.ts

provides:
  - TerminalStore MobX store managing panel visibility, active PTY session ID, and panel height
  - useTerminal hook: xterm.js Terminal lifecycle, PTY session creation, keyboard input wiring, resize via ResizeObserver
  - TerminalPanel observer component: fixed bottom panel, header bar with close button, Ctrl+` keyboard shortcut
  - Dynamic import of TerminalPanel into workspace-slug-layout (ssr: false)

affects: [35-cli-sidecar, 37-system-tray]

# Tech tracking
tech-stack:
  added:
    - "@xterm/xterm@5.5.0 — terminal emulator library (scoped, not deprecated unscoped xterm)"
    - "@xterm/addon-fit@0.11.0 — auto-sizes xterm Terminal to its container"
  patterns:
    - "All @xterm/* imports are dynamic (inside useEffect) — never top-level, prevents SSG errors"
    - "CSS module imported dynamically via import('@xterm/xterm/css/xterm.css') — needs css.d.ts type declaration"
    - "useRef holds Terminal and FitAddon instances (not useState) — avoids re-render on every output chunk"
    - "ResizeObserver wired pre-import resizeTerminal for sync callback compatibility"
    - "isCancelled flag prevents race condition if component unmounts during async init"
    - "TerminalPanel dynamically imported in layout (ssr: false) for SSG compatibility"

key-files:
  created:
    - frontend/src/stores/features/terminal/TerminalStore.ts
    - frontend/src/features/terminal/hooks/useTerminal.ts
    - frontend/src/features/terminal/components/TerminalPanel.tsx
    - frontend/src/types/css.d.ts
  modified:
    - frontend/package.json
    - frontend/pnpm-lock.yaml
    - frontend/src/stores/features/index.ts
    - frontend/src/stores/RootStore.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx

key-decisions:
  - "Dynamic-only xterm.js imports: all @xterm/* and IPC imports are inside useEffect/callbacks — prevents SSG build failures"
  - "useRef for Terminal/FitAddon instances: avoids re-render storms from frequent PTY output writes"
  - "isCancelled race-condition guard: protects against mount-before-init-completes and StrictMode double-mount"
  - "css.d.ts type declaration: resolves TypeScript TS2307 for dynamic CSS imports used by xterm.js"
  - "TerminalPanel ssr: false dynamic import: xterm.js requires DOM APIs unavailable during Next.js SSG"
  - "Close hides panel only — PTY session preserved in Rust backend across hide/show cycles"

patterns-established:
  - "Dynamic CSS import pattern: await import('lib/style.css') requires declare module '*.css' in types/*.d.ts"
  - "Terminal hook pattern: useRef for instances + useState for user-facing state (isReady, sessionId)"
  - "Tauri-only component pattern: return null if !isTauri() before any rendering logic"

requirements-completed: [TERM-01, TERM-03, TERM-04]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 34 Plan 02: Embedded Terminal Frontend Summary

**xterm.js terminal panel with MobX store, useTerminal lifecycle hook, and toggleable VS Code-style bottom panel wired into the Tauri desktop workspace layout**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T07:32:16Z
- **Completed:** 2026-03-20T07:36:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint auto-approved)
- **Files modified:** 9

## Accomplishments
- Installed @xterm/xterm@5.5.0 and @xterm/addon-fit@0.11.0 (scoped packages, not deprecated unscoped xterm)
- TerminalStore MobX store with isOpen, activeSessionId, panelHeight observables registered in RootStore
- useTerminal hook: full xterm.js lifecycle with 10,000-line scrollback, PTY session via Tauri IPC, keyboard input forwarding, ResizeObserver-based PTY resize, and safe cleanup on unmount
- TerminalPanel observer component: fixed bottom panel with header bar, Ctrl+` keyboard shortcut, isTauri() desktop gate
- Dynamically imported TerminalPanel (ssr: false) in workspace-slug-layout.tsx for SSG compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Install xterm.js packages, create TerminalStore and useTerminal hook** - `492afae0` (feat)
2. **Task 2: Create TerminalPanel component and wire into app layout** - `0a7b9f4d` (feat)
3. **Task 3: Verify terminal panel works end-to-end** - auto-approved (checkpoint:human-verify in --auto mode)

## Files Created/Modified
- `frontend/src/stores/features/terminal/TerminalStore.ts` - MobX store: isOpen, activeSessionId, panelHeight, toggle/open/close/reset actions
- `frontend/src/features/terminal/hooks/useTerminal.ts` - xterm.js lifecycle hook: Terminal creation, PTY session, input/output, resize, cleanup
- `frontend/src/features/terminal/components/TerminalPanel.tsx` - Observer component: bottom panel, header bar, close button, Ctrl+` shortcut
- `frontend/src/types/css.d.ts` - TypeScript declaration for dynamic CSS imports (needed for xterm.js CSS)
- `frontend/package.json` - Added @xterm/xterm@5.5.0 and @xterm/addon-fit@0.11.0
- `frontend/src/stores/features/index.ts` - Added TerminalStore export
- `frontend/src/stores/RootStore.ts` - Added terminal: TerminalStore field, constructor init, reset(), useTerminalStore() hook
- `frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx` - Added dynamic TerminalPanel import and conditional render

## Decisions Made
- Dynamic-only xterm.js imports prevent SSG build failures — all @xterm/* inside useEffect
- useRef for Terminal/FitAddon instances avoids re-render on every PTY output chunk
- isCancelled flag guards against React StrictMode double-mount race condition
- css.d.ts type declaration resolves TypeScript TS2307 error for `@xterm/xterm/css/xterm.css`
- TerminalPanel uses ssr: false dynamic import in layout.tsx — xterm needs DOM APIs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added css.d.ts type declaration for dynamic CSS import**
- **Found during:** Task 1 (useTerminal hook TypeScript verification)
- **Issue:** `await import('@xterm/xterm/css/xterm.css')` caused TypeScript TS2307 error — no module declaration for .css files
- **Fix:** Created `frontend/src/types/css.d.ts` with `declare module '*.css'` to satisfy TypeScript's module resolution
- **Files modified:** frontend/src/types/css.d.ts (created)
- **Verification:** `tsc --noEmit` passes with no errors
- **Committed in:** 492afae0 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for TypeScript compilation. The css.d.ts pattern is standard practice for dynamic CSS imports in TypeScript projects.

## Issues Encountered
None beyond the CSS type declaration auto-fix above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full xterm.js terminal panel complete (TERM-01, TERM-03, TERM-04)
- Rust PTY backend (Plan 34-01) + frontend (Plan 34-02) form complete embedded terminal stack
- Phase 35 (CLI Sidecar) can now build on top of the terminal infrastructure
- Phase 37 (System Tray) can reference terminal state via terminalStore.isOpen

## Self-Check: PASSED

All files verified to exist on disk. Both task commits verified in git log.

---
*Phase: 34-embedded-terminal*
*Completed: 2026-03-20*
