# Release Versioning Design

**Date:** 2026-02-26
**Status:** Approved
**Scope:** CHANGELOG.md + release script + initial v0.1.0-alpha.1 tag

---

## Context

Pilot Space has 31 conventional commits across 5 logical release milestones (Jan–Feb 2026) but no `CHANGELOG.md`, inconsistent git tags (`v0.0.4`, `0.0.4-fixed`, `dev-v0.0.1`), and no release automation. Both `frontend/package.json` and `backend/pyproject.toml` declare `0.1.0` but no corresponding tag exists.

## Goals

1. Write `CHANGELOG.md` at repo root following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) with all history back-filled
2. Tag current HEAD as `v0.1.0-alpha.1`
3. Add `scripts/release.sh` to automate future release mechanics while keeping changelog text fully manual

## Non-Goals

- Automated changelog generation from commits (git-cliff)
- CI/CD release pipeline

---

## Changelog Format

[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format with sections per release:

- **Added** — new features
- **Changed** — changed behavior in existing features
- **Fixed** — bug fixes
- **Security** — security vulnerability fixes
- **Deprecated** — soon-to-be removed features
- **Removed** — removed features

Sections only included when they have content.

---

## Version History

| Version | Date | Tag source | Key milestone |
|---------|------|------------|---------------|
| `0.1.0-alpha.1` | 2026-02-26 | New — this release | Note-First Issue Detail + GitHub integration + security |
| `0.0.4` | 2026-02-11 | `v0.0.4` + `0.0.4-fixed` merged | PM Note Extensions, approval UX, AI DI split |
| `0.0.3` | 2026-02-06 | `0.0.3` | Onboarding launch, role-skills, homepage hub |
| `0.0.2` | 2026-02-04 | `v0.0.2` | Conversational agent architecture (PilotSpaceAgent) |
| `0.0.1` | 2026-01-25 | `dev-v0.0.1` | MVP beta — full Note Canvas + Issue management + AI infra |

---

## `scripts/release.sh` Behavior

Usage: `./scripts/release.sh <version>`

Example: `./scripts/release.sh 0.1.1-alpha.2`

Steps (in order):

1. Validate argument is provided
2. Validate git working tree is clean (no uncommitted changes)
3. Check `[Unreleased]` section in `CHANGELOG.md` is non-empty (fail if empty)
4. Extract `[Unreleased]` section content (used for GitHub release notes)
5. Rename `[Unreleased]` → `[VERSION] - YYYY-MM-DD` in CHANGELOG.md
6. Insert new empty `[Unreleased]` section above it
7. Bump `version` in `frontend/package.json` (using `jq` or `sed`)
8. Bump `version` in `backend/pyproject.toml` (using `sed`)
9. `git add CHANGELOG.md frontend/package.json backend/pyproject.toml`
10. `git commit -m "chore(release): v{VERSION}"`
11. `git tag -a v{VERSION} -m "Release v{VERSION}"`
12. `git push && git push --tags`
13. `gh release create v{VERSION} --title "Pilot Space v{VERSION}" --notes "{extracted}" [--prerelease if alpha/beta in version]`

---

## File Changes

| File | Action |
|------|--------|
| `CHANGELOG.md` | Create (root of repo) |
| `scripts/release.sh` | Create (executable) |
| `docs/plans/2026-02-26-release-versioning-design.md` | This file |
