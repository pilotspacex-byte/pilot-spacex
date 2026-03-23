# Phase 35: Pilot CLI Sidecar - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

Compile the pilot CLI (Python, uv-managed) into a standalone binary using PyInstaller --onedir mode, ship it as a Tauri sidecar, and create the Rust spawn/streaming infrastructure. CI matrix produces per-platform binaries. No Python required on user's machine.

</domain>

<decisions>
## Implementation Decisions

### PyInstaller Build
- Use PyInstaller 6.19.0 with `--onedir` mode (NOT `--onefile` — research pitfall: incompatible with Tauri sidecar on Windows)
- Create `cli/pilot.spec` PyInstaller spec file
- Output binary name: `pilot-cli` (+ platform triple suffix for Tauri)
- Hidden imports for all pilot CLI dependencies

### Sidecar Configuration
- Tauri `externalBin` config in `tauri.conf.json` pointing to `binaries/pilot-cli`
- Binary naming: `pilot-cli-{arch}-{os}` (e.g., `pilot-cli-aarch64-apple-darwin`)
- Binaries stored in `tauri-app/binaries/` (gitignored, produced by CI)

### Rust Sidecar Module
- `commands/sidecar.rs` — spawn pilot-cli sidecar with args
- Stream stdout/stderr to frontend via `tauri::ipc::Channel`
- Track running processes for cancellation
- Exit code reporting

### CI Pipeline
- 4 platform runners (macOS ARM, macOS Intel, Linux x64, Windows x64)
- Each runner: install uv → `uv sync` → PyInstaller build → upload artifact
- Artifacts consumed by tauri-build.yml (Phase 30's CI)

### Claude's Discretion
- PyInstaller hidden imports list
- Sidecar process cleanup on app quit
- Binary size optimization strategies

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/` directory — existing pilot CLI source (pyproject.toml, src/)
- `tauri-app/src-tauri/src/commands/terminal.rs` — streaming output pattern (Phase 34)
- `.github/workflows/tauri-build.yml` — existing CI matrix (Phase 30)

### Established Patterns
- Channel-based streaming for process output
- `spawn_blocking` for blocking operations
- IPC wrappers in tauri.ts

### Integration Points
- `tauri.conf.json` — add `bundle.externalBin` config
- `.github/workflows/tauri-build.yml` — add PyInstaller build step before Tauri build
- Phase 37 will use this sidecar for the one-click implement flow

</code_context>

<specifics>
## Specific Ideas

- Research warns: macOS sidecar binaries need individual code signing (Tauri bug #11992)
- Research warns: PyInstaller binaries trigger Windows AV false positives — `--onedir` reduces this
- The pilot CLI currently uses `pilot login` and `pilot implement <issue-id>`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 35-pilot-cli-sidecar*
*Context gathered: 2026-03-20 via autonomous mode*
