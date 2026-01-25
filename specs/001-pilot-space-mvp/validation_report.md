# MVP Scope Validation Report

**Date**: 2026-01-22
**Updated**: 2026-01-22 (Claude Agent SDK Deep Dive)
**Target**: `specs/001-pilot-space-mvp`
**Documents Reviewed**:
- `docs/architect/ai-layer.md`
- `docs/PILOT_SPACE_FEATURES.md`
- `docs/AI_CAPABILITIES.md`
- `docs/DESIGN_DECISIONS.md`
- `docs/PROJECT_VISION.md`

## Summary
The design documents are largely consistent with the MVP specification (`001-pilot-space-mvp`), adhering to the "Note-First" philosophy and BYOK AI model. Critical architectural inconsistencies were identified regarding Claude Agent SDK usage and have been resolved in DD-002 (updated) and DD-058 (new).

## Consistency Checks

| Feature | Spec / DD | Design Docs | Status |
|---------|-----------|-------------|--------|
| **AI PR Review** | Unified Arch + Code Review (DD-006) | Lists separate agents (`AI_CAPABILITIES.md`) | ⚠️ Inconsistent |
| **Integrations** | GitHub + Slack Only (DD-004) | Diagram implies full suite (`PILOT_SPACE_FEATURES.md`) | ⚠️ Needs Clarification |
| **Real-time Collab** | Excluded/Post-MVP (DD-005) | Consistent | ✅ Pass |
| **AI Agents** | "9 Primary + 7 Helper = 16 Total" | Consistent across all docs | ✅ **Fixed** |
| **Tech Stack** | FastAPI/Supabase/Next.js | Consistent | ✅ Pass |
| **BYOK Providers** | OpenAI, Anthropic, Google, Azure (DD-002) | Missing Google in old DD-002 | ✅ **Fixed** |
| **Claude Agent SDK** | Orchestrator for agentic tasks | Mixed with non-Claude providers | ✅ **Fixed (DD-058)** |

---

## Critical: Claude Agent SDK Inconsistencies (DD-058)

### Issue 1: GhostTextAgent Provider Mismatch
**Problem**: `ai-layer.md` shows `GhostTextAgent` using `ClaudeAgentOptions` but routing to Google Gemini Flash. Claude Agent SDK is Anthropic-only.

**Resolution**: Non-agentic tasks (ghost text, annotations) use direct Google SDK, not Claude Agent SDK.

### Issue 2: Embeddings Cannot Route Through Claude SDK
**Problem**: `LLMProvider.embed()` method expected to use Claude SDK, but embeddings must use OpenAI for best 3072-dim quality.

**Resolution**: Separate `EmbeddingService` class using OpenAI SDK directly.

### Issue 3: Provider Routing Conflicts with SDK Constraints
**Problem**: `ProviderSelector.ROUTING_TABLE` implies any task can use any provider, but Claude Agent SDK only works with Anthropic models.

**Resolution**: Split into **Agentic Tasks** (Claude SDK required) vs **Non-Agentic Tasks** (direct provider SDKs).

### Issue 4: API Key Dependency Hierarchy Unclear
**Problem**: All providers appeared optional, but Anthropic key is required for core agentic features.

**Resolution**: Document dependency hierarchy:
- **Required**: Anthropic (orchestration), OpenAI (embeddings)
- **Recommended**: Google (latency-critical tasks)
- **Optional**: Azure (enterprise fallback)

### Issue 5: Unified LLMProvider Abstraction is Leaky
**Problem**: Abstract `LLMProvider` tries to unify Claude SDK with other providers.

**Resolution**: Replace with explicit `AIOrchestrator` pattern with provider-specific clients.

---

## Provider Routing Architecture (Corrected)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI ORCHESTRATOR                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  AGENTIC TASKS (require MCP tools)          NON-AGENTIC TASKS               │
│  ──────────────────────────────────         ───────────────────────────     │
│                                                                              │
│  ┌──────────────────────────────┐           ┌───────────────────────────┐   │
│  │  Claude Agent SDK            │           │  Direct Provider SDKs     │   │
│  │  (Anthropic Required)        │           │                           │   │
│  │                              │           │  • Google Gemini Flash    │   │
│  │  • PR Review                 │           │    → Ghost Text           │   │
│  │  • Task Decomposition        │           │    → Margin Annotations   │   │
│  │  • AI Context                │           │    → Notification Priority│   │
│  │  • Issue Extraction          │           │                           │   │
│  │  • Doc Generation            │           │  • OpenAI Embeddings      │   │
│  │                              │           │    → 3072-dim vectors     │   │
│  │  MCP Tools:                  │           │    → RAG indexing         │   │
│  │  • get_issue_context         │           │                           │   │
│  │  • get_note_content          │           │  • Claude (non-agentic)   │   │
│  │  • create_note_annotation    │           │    → Simple generation    │   │
│  │  • search_codebase           │           │    → Diagrams             │   │
│  └──────────────────────────────┘           └───────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Discrepancies & Resolutions

### 1. Unified PR Review Agent
- **Issue**: `AI_CAPABILITIES.md` describes "Architecture Review Agent" and "Code Review Agent" as separate entities. `DD-006` and implementation plan (`ai-layer.md`) unify them into a single `PRReviewAgent`.
- **Resolution**: Update `AI_CAPABILITIES.md` and `PILOT_SPACE_FEATURES.md` to reflect the unified implementation while acknowledging they cover distinct domains (Architecture & Code).

### 2. Implementation Agent Count
- **Issue**: `ai-layer.md` table lists 16 agents, text claims 14, and `spec.md` references 9 user-facing agents.
- **Resolution**: **FIXED** - All documents now consistently use 16 agents. Updated README.md, plan.md to match ai-layer.md agent catalog.

### 3. Integration Scope in Features Doc
- **Issue**: `PILOT_SPACE_FEATURES.md` high-level diagrams show "VCS", "Comm", "CI/CD" without MVP constraints.
- **Resolution**: Add explicit "MVP Scope" note to Integrations section in `PILOT_SPACE_FEATURES.md` referencing `DD-004`.

### 4. Google Gemini Provider Missing from DD-002
- **Issue**: Original DD-002 only listed OpenAI, Anthropic, Azure OpenAI.
- **Resolution**: **FIXED** - Updated DD-002 to include Google Gemini with clear routing rules.

### 5. Claude Agent SDK Architecture Inconsistencies
- **Issue**: Multiple architectural inconsistencies in provider abstraction, routing, and SDK usage.
- **Resolution**: **FIXED** - Added DD-058 documenting all issues and their resolutions.

---

## Action Plan

| # | Action | Document | Status |
|---|--------|----------|--------|
| 1 | Update DD-002 with Google Gemini + Claude SDK orchestration | `DESIGN_DECISIONS.md` | ✅ **Done** |
| 2 | Add DD-058 Claude Agent SDK Inconsistencies | `DESIGN_DECISIONS.md` | ✅ **Done** |
| 3 | Update Agent Pool diagram to show unified PRReviewAgent | `AI_CAPABILITIES.md` | ✅ **Done** |
| 4 | Mark Pattern Matcher Agent as Phase 2 | `AI_CAPABILITIES.md` | ✅ **Done** |
| 5 | Mark Retro Analyst Agent as Phase 2 | `AI_CAPABILITIES.md` | ✅ **Done** |
| 6 | Refine `ai-layer.md`: Fix GhostTextAgent to use Google SDK directly | `ai-layer.md` | 🔲 Pending |
| 7 | Refine `ai-layer.md`: Remove unified LLMProvider abstraction | `ai-layer.md` | 🔲 Pending |
| 8 | Update onboarding to mark Anthropic + OpenAI keys as required | `spec.md` | 🔲 Pending |

---

## Design Decisions Summary (AI-Related)

| DD | Title | Status |
|----|-------|--------|
| DD-002 | BYOK with Claude Agent SDK Orchestration | ✅ Updated |
| DD-003 | AI Autonomy Model - Critical-Only Approval | ✅ No Change |
| DD-006 | Unified PR Review (Arch + Code + Security + Perf + Docs) | ✅ No Change |
| DD-011 | Provider Routing (Claude→code, Gemini→latency, OpenAI→embeddings) | ✅ Aligned |
| DD-048 | AI Confidence Tags Display | ✅ No Change |
| DD-058 | Claude Agent SDK Inconsistencies Resolution | ✅ **New** |

**Comprehensive Documentation**: See [claude-agent-sdk-architecture.md](../../docs/architect/claude-agent-sdk-architecture.md) for detailed:
- BYOK architecture and key storage
- Human-in-the-loop approval patterns (DD-003)
- Unified PR Review implementation (DD-006)
- Provider routing rules (DD-011)
- MCP tool specifications

---

*Report Version: 2.1*
*Last Updated: 2026-01-22*
