---
phase: quick-9
plan: "01"
subsystem: knowledge-graph
tags: [chunker, contextual-retrieval, embedding, byok, tdd]
dependency_graph:
  requires: []
  provides:
    - "_merge_atomic_blocks in markdown_chunker — code block and table preservation"
    - "contextual_enrichment.enrich_chunks_with_context — LLM context prefix per chunk"
  affects:
    - "backend/src/pilot_space/infrastructure/queue/handlers/kg_populate_handler.py"
    - "backend/src/pilot_space/ai/workers/memory_worker.py"
    - "backend/src/pilot_space/main.py"
tech_stack:
  added:
    - "anthropic.AsyncAnthropic — direct client for context enrichment"
    - "_merge_atomic_blocks — paragraph merging for atomic block detection"
  patterns:
    - "BYOK graceful degradation (api_key=None → skip LLM)"
    - "asyncio.gather with return_exceptions=True for parallel LLM calls"
    - "TDD RED→GREEN per task"
key_files:
  created:
    - "backend/src/pilot_space/application/services/note/contextual_enrichment.py"
    - "backend/tests/unit/services/test_contextual_enrichment.py"
  modified:
    - "backend/src/pilot_space/application/services/note/markdown_chunker.py"
    - "backend/tests/unit/services/test_markdown_chunker.py"
    - "backend/src/pilot_space/infrastructure/queue/handlers/kg_populate_handler.py"
    - "backend/src/pilot_space/ai/workers/memory_worker.py"
    - "backend/src/pilot_space/main.py"
decisions:
  - "Use getattr(block, 'text', '') instead of block.text to handle Anthropic SDK union types (ThinkingBlock, ToolUseBlock, etc.) without pyright errors"
  - "Local _estimate_tokens() in contextual_enrichment instead of importing private _count_tokens from chunker — avoids reportPrivateUsage pyright error"
  - "Replace asyncio.TimeoutError with builtin TimeoutError per ruff UP041 rule"
  - "Use # pragma: allowlist secret on module-level fake key constant instead of inline in function calls (Python syntax constraint)"
metrics:
  duration: "9 minutes"
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_changed: 7
---

# Phase quick-9 Plan 01: Enhance Chunker with Contextual Retrieval Summary

**One-liner:** Atomic block preservation (code fences + tables) in chunker via `_merge_atomic_blocks`, plus LLM-generated context prefix per chunk via `enrich_chunks_with_context` using claude-haiku (BYOK, graceful degradation).

## What Was Built

### Task 1: Code Block and Table Preservation (TDD)

Added `_merge_atomic_blocks(paragraphs: list[str]) -> list[str]` to `markdown_chunker.py`.

The function post-processes the `content.split("\n\n")` result before paragraph iteration in `_sub_chunk_by_paragraphs`:

- **Code fences**: Detects lines starting with 3+ backticks (with or without language tag). Tracks `in_code_fence` state. Accumulates paragraphs until the closing fence. Handles unclosed fences defensively (everything after opener stays together).
- **Markdown tables**: Detects paragraphs where all non-empty lines start with `|`. Merges consecutive table paragraphs into one atomic block.

Result: fenced code blocks with internal blank lines and multi-row markdown tables are never split across sub-chunks.

### Task 2: Contextual Enrichment Module and KG Pipeline Wiring (TDD)

Created `contextual_enrichment.py` with:

```
enrich_chunks_with_context(
    chunks: list[MarkdownChunk],
    full_document: str,
    api_key: str | None = None,
    content_cap: int = 2000,
) -> list[MarkdownChunk]
```

- If `api_key is None` or `chunks` is empty: returns unchanged (BYOK).
- Calls `anthropic.AsyncAnthropic` for each chunk in parallel via `asyncio.gather`.
- 15-second global timeout (`asyncio.wait_for`).
- Per-chunk failure returns original chunk — never fails the whole batch.
- Content cap: if `[Context: ...]\n\n{content}` exceeds `content_cap`, context is truncated to fit.
- Returns new frozen `MarkdownChunk` instances with enriched content and updated `token_count`.

Wired into:
- `KgPopulateHandler.__init__` — gains `anthropic_api_key: str | None = None`; enrichment called after chunking in `_handle_note` and `_handle_issue`
- `MemoryWorker.__init__` — gains `anthropic_api_key`; passes to `KgPopulateHandler`
- `main.py` — extracts `anthropic_api_key` from settings (same pattern as `google_api_key`)

## Test Coverage

| Test class | Tests | Location |
|---|---|---|
| TestCodeBlockPreservation | 5 | test_markdown_chunker.py |
| TestTablePreservation | 4 | test_markdown_chunker.py |
| TestEnrichChunksWithContext | 9 | test_contextual_enrichment.py |
| (existing chunker tests) | 34 | test_markdown_chunker.py |
| **Total** | **52** | |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pyright errors on Anthropic response content access**
- **Found during:** Task 2 quality gates
- **Issue:** `response.content[0].text` fails pyright — `content[0]` is a union of `TextBlock | ThinkingBlock | ToolUseBlock | ...` and not all have `.text`
- **Fix:** Changed to `getattr(first_block, "text", "").strip()` which is safe across all block types
- **Files modified:** `contextual_enrichment.py`
- **Commit:** cfba3e28

**2. [Rule 1 - Bug] Imported private `_count_tokens` from chunker**
- **Found during:** Task 2 quality gates
- **Issue:** `reportPrivateUsage` pyright error — `_count_tokens` is module-private
- **Fix:** Added local `_estimate_tokens(text: str) -> int` in `contextual_enrichment.py` (same `len // 4` formula)
- **Files modified:** `contextual_enrichment.py`
- **Commit:** cfba3e28

**3. [Rule 3 - Lint] `asyncio.TimeoutError` deprecated by ruff UP041**
- **Found during:** Task 2 quality gates
- **Issue:** ruff UP041 requires using builtin `TimeoutError` instead of `asyncio.TimeoutError`
- **Fix:** Changed `except asyncio.TimeoutError` to `except TimeoutError`
- **Files modified:** `contextual_enrichment.py`
- **Commit:** cfba3e28

**4. [Rule 3 - Lint] detect-secrets false positive on test API key**
- **Found during:** Task 2 RED phase commit
- **Issue:** `api_key="sk-test"` in function call arguments — can't use inline `# pragma` inside closing paren
- **Fix:** Extracted `_FAKE_API_KEY = "sk-ant-test-key"  # pragma: allowlist secret` as module-level constant; all test calls use the constant
- **Files modified:** `test_contextual_enrichment.py`
- **Commit:** ae458115

## Self-Check: PASSED

- [x] `contextual_enrichment.py` exists
- [x] `test_contextual_enrichment.py` exists
- [x] Commit cfba3e28 exists (Task 2 implementation)
- [x] Commit 4ef61189 exists (Task 1 implementation)
- [x] 52 tests pass (43 chunker + 9 enrichment)
- [x] pyright: 0 errors on all modified files
- [x] ruff: all checks passed
