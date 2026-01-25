# Getting Started with Pilot Space

**Version**: 1.0 | **Date**: 2026-01-23

---

## Welcome to Pilot Space! 🚀

Pilot Space is an AI-augmented development platform that transforms how teams capture, clarify, and track work. Instead of starting with forms and tickets, you start with **notes**—rough ideas that AI helps refine into clear, actionable issues.

---

## Quick Start (5 minutes)

### Step 1: Create Your Workspace

1. Sign up at [app.pilotspace.io](https://app.pilotspace.io)
2. Click **"Create Workspace"**
3. Enter your workspace name (e.g., "Acme Engineering")
4. Invite team members (optional for now)

### Step 2: Configure AI (BYOK)

Pilot Space uses a **Bring Your Own Key** model for AI features. You'll need API keys from AI providers.

1. Go to **Settings** → **AI Configuration**
2. Add your API keys:

| Provider | Required | Purpose |
|----------|----------|---------|
| **Anthropic** | ✅ Yes | Code review, task planning |
| **OpenAI** | ✅ Yes | Search and embeddings |
| **Google** | ⭕ Recommended | Fast typing suggestions |

**Getting API Keys**:
- [Anthropic Console](https://console.anthropic.com/) → API Keys
- [OpenAI Platform](https://platform.openai.com/) → API Keys
- [Google AI Studio](https://aistudio.google.com/) → Get API Key

3. Click **"Validate Keys"** to verify they work
4. Save your configuration

### Step 3: Create Your First Project

1. Click **"New Project"**
2. Enter project details:
   - **Name**: "Backend API" (your project name)
   - **Identifier**: "API" (short code for issues, e.g., API-123)
   - **Description**: Brief project description

### Step 4: Write Your First Note

This is where Pilot Space shines! 🌟

1. Click **"New Note"** (or press `N`)
2. Start typing your thoughts:

```
We need to implement user authentication.

The current system has no login, anyone can access
everything. We should probably use SSO since most
of our team uses Google Workspace.

Things to consider:
- How do we handle existing users?
- What about API authentication for integrations?
- Mobile app support later?
```

3. Watch the magic happen:
   - **Ghost text** appears as you type (press Tab to accept)
   - **AI annotations** appear in the margin with questions
   - Click an annotation to discuss with AI

### Step 5: Extract Issues

1. Look for the margin counter: "3 issues detected"
2. Click **"Review"** to see detected issues
3. Each issue is highlighted with a rainbow border
4. Review the AI-suggested title and description
5. Click **"Accept"** to create the issue, or edit first

Congratulations! You've just extracted structured issues from your rough notes. 🎉

---

## Core Workflow: Note-First

```
┌─────────────────────────────────────────────────────────────┐
│                     THE NOTE-FIRST FLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. WRITE           2. CLARIFY          3. EXTRACT         │
│   ──────────         ──────────          ──────────         │
│                                                              │
│   Your rough    →    AI asks         →   Structured         │
│   ideas              questions           issues emerge       │
│                                                              │
│   "We need           "What's             • SSO Integration   │
│    better auth"       driving this?"     • User Migration    │
│                                          • API Auth Design   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Why Note-First?

| Traditional Tools | Pilot Space |
|-------------------|-------------|
| Start with empty form | Start with your thoughts |
| "What's the title?" | "Just write what you're thinking" |
| Context lost in ticket | Context preserved in note |
| AI adds labels after | AI clarifies before |

---

## Key Features

### Ghost Text (Inline AI Suggestions)

As you type, AI suggests completions:

- **Trigger**: Pause typing for 500ms
- **Accept all**: Press `Tab`
- **Accept one word**: Press `→` (right arrow)
- **Dismiss**: Keep typing

### Margin Annotations

AI asks clarifying questions in the margin:

- 🔵 **Questions**: "What's the priority here?"
- 🟡 **Suggestions**: "Consider adding acceptance criteria"
- 🟢 **Insights**: "Similar to issue AUTH-45"

Click any annotation to start a threaded discussion.

### Issue Extraction

When AI detects actionable items:

1. Margin shows: "3 issues detected"
2. Click **Review** to see highlighted text
3. Each potential issue has a rainbow border
4. Review, edit, or skip each one
5. Accepted issues link back to the source note

### AI Code Review

When you link a GitHub repository:

1. Open a Pull Request
2. AI automatically reviews within 5 minutes
3. Comments appear inline on the PR
4. Covers: architecture, security, quality, performance

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Command Palette | `Cmd+K` |
| New Note | `N` |
| New Issue | `I` |
| Search | `Cmd+/` |
| Save | `Cmd+S` |
| Accept Ghost Text | `Tab` |
| Accept Word | `→` |
| Undo | `Cmd+Z` |

---

## Integrations

### GitHub

Connect your repositories for:
- Automatic commit linking (mention `API-123` in commits)
- AI PR review on every pull request
- PR merge auto-completes linked issues

**Setup**: Settings → Integrations → GitHub → Install App

### Slack

Get notified and create issues from Slack:
- Notifications for assignments, comments, PR reviews
- `/pilot create` - Create issue from Slack
- Link unfurling for Pilot Space URLs

**Setup**: Settings → Integrations → Slack → Add to Slack

---

## Tips for Success

### 1. Start Messy
Don't worry about structure. Write your thoughts naturally. AI will help organize.

### 2. Engage with AI Questions
The margin annotations aren't just suggestions—they're helping you clarify your own thinking.

### 3. Review Before Accepting
AI suggestions are starting points. Your domain expertise refines them.

### 4. Link Everything
Notes to issues, issues to PRs, PRs to commits. Pilot Space tracks relationships.

### 5. Use the Command Palette
`Cmd+K` is your friend. Quick access to everything.

---

## Getting Help

- **In-app**: Click `?` in the bottom-right corner
- **Documentation**: [docs.pilotspace.io](https://docs.pilotspace.io)
- **Community**: [community.pilotspace.io](https://community.pilotspace.io)
- **Support**: support@pilotspace.io

---

## Next Steps

- [Note-First Workflow Guide](./note-first-workflow.md) - Deep dive into the workflow
- [AI Capabilities](./ai-capabilities.md) - All AI features explained
- [Team Onboarding](./team-onboarding.md) - Inviting and managing your team
