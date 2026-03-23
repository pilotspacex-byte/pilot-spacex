# Phase 39: Tech Debt Cleanup - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Infrastructure phase — gap closure from v1.1-MILESTONE-AUDIT.md

<domain>
## Phase Boundary

Close 3 tech debt items from milestone audit: generate Tauri updater signing keypair and commit pubkey, add missing barrel exports to stores/index.ts, and wire sidecar download into dev CI workflow.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure/cleanup phase.

</decisions>

<specifics>
## Specific Ideas

1. **Auto-update pubkey**: Run `npx tauri signer generate` to create a keypair, commit the public key to `tauri.conf.json plugins.updater.pubkey`. The private key goes to GitHub secrets (document but don't commit).

2. **stores/index.ts**: Add `TerminalStore`, `useTerminalStore`, `ImplementStore`, `useImplementStore` exports to match the pattern already used for `ProjectStore`, `GitStore`.

3. **Dev CI sidecar**: Add a step to `tauri-build.yml` that downloads the pilot-cli artifact from `pilot-cli-build.yml` (using `actions/download-artifact` or `dawidd6/action-download-artifact` for cross-workflow downloads). This ensures dev/PR builds include the real sidecar binary, not the empty stub.

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 39-tech-debt-cleanup*
*Context gathered: 2026-03-20 via autonomous mode*
