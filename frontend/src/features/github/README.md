# GitHub Integration Module

_For project overview, see main `README.md` and `frontend/README.md`_

## Purpose

GitHub integration for OAuth connection, repository management, PR-to-issue linking, and AI-powered PR review with GitHub comments.

**Design Decisions**: DD-004 (MVP scope), DD-011 (provider routing)

---

## Module Structure

```
frontend/src/features/github/
├── pages/
│   └── github-settings-page.tsx   # OAuth + repo management
├── components/
│   ├── github-connect-button.tsx  # OAuth trigger
│   ├── repo-selector.tsx          # Repo list + sync toggle
│   ├── pr-link-card.tsx           # Link PR to issue
│   ├── pr-review-status.tsx       # Review status display
│   └── webhook-status.tsx         # Connection status
├── hooks/
│   ├── useGitHubAuth.ts           # OAuth + token management
│   ├── useGitHubRepos.ts          # Fetch repos
│   ├── useLinkPR.ts               # Link PR to issue mutation
│   └── usePRReview.ts             # PR review results
└── __tests__/
```

---

## Features

### OAuth Flow

Connect GitHub -> OAuth popup -> user grants permissions (repos:read, pull_requests:write, workflow:read) -> redirect with code -> backend exchanges for token -> stored in Supabase Vault (encrypted) -> repo list refreshes.

**UI States**: Not Connected (button), Connecting (spinner), Connected (repo list), Error (retry).

### Repository Management

List repos, sync toggle (enable/disable for PR linking), webhook status indicator, manual refresh. Sync on: register webhook + listen for PR events. Sync off: optionally unregister webhook.

### PR Linking

In issue detail sidebar "Linked PRs" section. Search by `github-org/repo-name#123`, fetch from GitHub API, confirm link -> creates `IssueGitHubPRLink` record.

### PR Review (AI)

Triggered by GitHub webhook (PR opened/updated) -> backend queues (pgmq) -> PRReviewAgent (Claude Opus) analyzes -> comments posted to GitHub PR -> SSE notification to frontend. Severity: Critical (red), Warning (yellow), Info (green).

---

## API Endpoints

```
POST   /github/oauth/authorize          -> { oauth_url }
GET    /github/repos                     -> GitHubRepository[]
PATCH  /github/repos/{repoId}/settings   -> GitHubRepository
POST   /github/pr/link                   -> IssueGitHubPRLink
GET    /github/pr/{owner}/{repo}/{number} -> GitHubPR
DELETE /github/pr/link/{linkId}
```

---

## State Management

**GitHubStore** (MobX): See `stores/` for `isConnected`, `repos`, `linkedPRs` (Map by issue ID), and actions (connect, disconnect, loadRepos, syncSettings, linkPR, unlinkPR).

---

## Related Documentation

- `docs/architect/frontend-architecture.md`
- `docs/dev-pattern/45-pilot-space-patterns.md`
