---
phase: 35-pilot-cli-sidecar
plan: "01"
subsystem: cli-build
tags: [pyinstaller, ci, sidecar, tauri, cross-platform]
dependency_graph:
  requires: []
  provides: [cli/pilot.spec, .github/workflows/pilot-cli-build.yml, tauri-app/src-tauri/binaries/]
  affects: [tauri-app/src-tauri/tauri.conf.json]
tech_stack:
  added: [PyInstaller>=6.19.0]
  patterns: [onedir-sidecar, matrix-ci, env-var-injection-safe]
key_files:
  created:
    - cli/pilot.spec
    - .github/workflows/pilot-cli-build.yml
    - tauri-app/src-tauri/binaries/.gitkeep
  modified:
    - .gitignore
decisions:
  - "onedir mode chosen over --onefile: Tauri sidecar on Windows requires unpacked binary directory (--onefile causes DLL extraction issues at runtime)"
  - "PyGithub/nacl hidden imports removed: github_client.py uses httpx directly, not PyGithub — import list matches actual runtime deps"
  - "pilot_cli.backup.* subpackage explicitly listed in hiddenimports: PyInstaller static analysis misses dynamic imports inside conditional code paths"
  - "!cli/pilot.spec negation added to .gitignore: root .gitignore had *.spec pattern that would suppress the spec file"
  - "Matrix env vars used in CI run: steps instead of inline ${{ matrix.* }} expressions: satisfies security hook requirement to prevent injection"
metrics:
  duration: "3 minutes"
  completed: "2026-03-20"
  tasks_completed: 2
  files_created: 3
  files_modified: 1
---

# Phase 35 Plan 01: PyInstaller Spec and CI Sidecar Build Summary

PyInstaller onedir spec + 4-platform GitHub Actions CI matrix that compiles pilot-cli into Tauri-compatible sidecar binaries named with Rust target triple suffixes.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create PyInstaller spec and binaries directory | b4a94ee5 | cli/pilot.spec, tauri-app/src-tauri/binaries/.gitkeep, .gitignore |
| 2 | Create CI workflow for cross-platform builds | 2eb72e27 | .github/workflows/pilot-cli-build.yml |

## What Was Built

### cli/pilot.spec

PyInstaller onedir spec that compiles `cli/src/pilot_cli/main.py` into a standalone binary bundle at `dist/pilot-cli/`. Key design:

- **onedir mode** (`exclude_binaries=True` + `COLLECT`): produces a directory with the main binary + shared libs, not a single compressed file. Required for Tauri sidecar on Windows (avoids DLL extraction failures at startup).
- **Hidden imports**: covers all transitive deps that PyInstaller's static analysis misses — typer/click, httpx/httpcore/h11, rich/pygments, git/gitdb/smmap, jinja2/markupsafe, tomli_w, cryptography (full hazmat chain), and all pilot_cli submodules including the backup subpackage.
- **Datas**: `pilot_cli/templates/` included for the `implement` command's Jinja2 `CLAUDE_MD_TEMPLATE.md`.
- **Excludes**: pytest, pytest_asyncio, respx, mypy, ruff, pytest_cov, tkinter, unittest — dev-only modules that inflate binary size.

### .github/workflows/pilot-cli-build.yml

4-runner CI matrix matching the existing `tauri-build.yml` platform selection:

| Runner | Target Triple | Binary |
|--------|--------------|--------|
| macos-latest | aarch64-apple-darwin | pilot-cli-aarch64-apple-darwin |
| macos-13 | x86_64-apple-darwin | pilot-cli-x86_64-apple-darwin |
| ubuntu-22.04 | x86_64-unknown-linux-gnu | pilot-cli-x86_64-unknown-linux-gnu |
| windows-latest | x86_64-pc-windows-msvc | pilot-cli-x86_64-pc-windows-msvc.exe |

Each runner: installs Python 3.12 + uv, runs `uv sync` + `uv pip install pyinstaller>=6.19.0`, builds via `uv run pyinstaller pilot.spec --noconfirm --clean`, renames the binary with the Tauri target triple suffix, uploads both the renamed binary and the onedir support file bundle as artifacts, then smoke-tests with `--help`.

### tauri-app/src-tauri/binaries/

Created with `.gitkeep`. The `pilot-cli-*` glob is gitignored (CI-built, not committed). Phase 36 will configure `tauri.conf.json` to reference these sidecar binaries.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added pilot_cli.backup.* subpackage to hidden imports**
- **Found during:** Task 1 — reading backup.py imports
- **Issue:** The plan's hidden imports list covered main commands but omitted the backup subpackage (archive, encryption, pg_backup, storage_backup). PyInstaller would fail to include them via static analysis since they're imported through the backup sub-app.
- **Fix:** Added `pilot_cli.backup`, `pilot_cli.backup.archive`, `pilot_cli.backup.encryption`, `pilot_cli.backup.pg_backup`, `pilot_cli.backup.storage_backup` to hiddenimports.
- **Files modified:** cli/pilot.spec

**2. [Rule 1 - Bug] Removed PyGithub/nacl from hidden imports; added rich.prompt**
- **Found during:** Task 1 — reading github_client.py
- **Issue:** `github_client.py` imports `httpx` directly (not PyGithub), so the `github`, `github.MainClass`, `urllib3`, `nacl` hidden imports in the plan spec were for a dependency that isn't used. Including unused hidden imports can pull in unnecessary modules and inflate the binary. Additionally, `login.py` imports `rich.prompt` which was missing.
- **Fix:** Removed `github`, `github.MainClass`, `urllib3`, `nacl` from hiddenimports. Added `rich.prompt`.
- **Files modified:** cli/pilot.spec

**3. [Rule 2 - Missing Critical Functionality] Added !cli/pilot.spec negation to .gitignore**
- **Found during:** Task 1 — reading .gitignore
- **Issue:** The root .gitignore already had `*.spec` (PyInstaller spec files are conventionally gitignored). Without a negation rule, `cli/pilot.spec` would be ignored and not tracked in git, causing the CI workflow to fail (the spec file would not be present on checkout).
- **Fix:** Added `!cli/pilot.spec` negation pattern after the tauri sidecar binaries gitignore block.
- **Files modified:** .gitignore

**4. [Rule 2 - Security] CI workflow uses env: vars in run: steps**
- **Found during:** Task 2 — security hook fired on Write attempt
- **Issue:** Using `${{ matrix.target_triple }}` directly in `run:` blocks is flagged by the project's security hook (GitHub Actions injection prevention). While matrix values are static, the security policy requires using `env:` with proper quoting.
- **Fix:** Added `env: TARGET_TRIPLE: ${{ matrix.target_triple }}` and `env: BINARY_EXT: ${{ matrix.binary_ext }}` blocks to all `run:` steps that use these values; referenced via `${TARGET_TRIPLE}` in shell.
- **Files modified:** .github/workflows/pilot-cli-build.yml

## Self-Check: PASSED

Files created:
- FOUND: cli/pilot.spec
- FOUND: tauri-app/src-tauri/binaries/.gitkeep
- FOUND: .github/workflows/pilot-cli-build.yml
- FOUND: .planning/phases/35-pilot-cli-sidecar/35-01-SUMMARY.md

Commits:
- FOUND: b4a94ee5
- FOUND: 2eb72e27
