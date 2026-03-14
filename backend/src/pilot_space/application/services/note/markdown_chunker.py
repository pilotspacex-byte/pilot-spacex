"""Markdown heading-based text chunker for Knowledge Graph ingestion.

Splits a Markdown document into subsections at heading boundaries using the
markdown-it-py AST (token.map line ranges). Each chunk carries its heading
text, level, position, heading hierarchy, and raw markdown content for embedding.

Improvements over naive splitting:
  1. Configurable overlap between chunks preserves context at boundaries.
  2. Recursive sub-chunking splits oversized sections at paragraph boundaries.
  3. Token-aware max size uses tiktoken when available, falls back to char count.
  4. Heading hierarchy enrichment adds parent headings as context prefix.
  5. Dynamic max chunks scales with document size instead of fixed cap.
  6. Code block preservation — fenced code blocks never split across sub-chunks.
  7. Table preservation — markdown tables never split mid-row.

Feature 016: Knowledge Graph — automated KG population from notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from markdown_it import MarkdownIt

__all__ = ["MarkdownChunk", "chunk_markdown_by_headings"]

_DEFAULT_MAX_CHUNKS = 20
_DYNAMIC_CHUNKS_PER_KB = 5  # 5 chunks per 1KB of source text
_DEFAULT_MAX_CHUNK_CHARS = 2000
_DEFAULT_OVERLAP_CHARS = 100
_MD = MarkdownIt("commonmark")

# Lazy-loaded tiktoken encoder (None if tiktoken unavailable)
_tiktoken_enc: object | None = None
_tiktoken_loaded = False


def _get_tiktoken_enc() -> object | None:
    """Lazy-load tiktoken cl100k_base encoder."""
    global _tiktoken_enc, _tiktoken_loaded  # noqa: PLW0603
    if _tiktoken_loaded:
        return _tiktoken_enc
    _tiktoken_loaded = True
    try:
        import tiktoken  # pyright: ignore[reportMissingImports]

        _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
    except (ImportError, Exception):
        _tiktoken_enc = None
    return _tiktoken_enc


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken if available, else estimate from char count."""
    enc = _get_tiktoken_enc()
    if enc is not None:
        return len(enc.encode(text))  # type: ignore[union-attr]
    # Rough estimate: 1 token ≈ 4 chars for English text
    return len(text) // 4


@dataclass(frozen=True, slots=True)
class MarkdownChunk:
    """One heading-bounded section of a Markdown document.

    Attributes:
        heading:           Heading text (empty string for preamble).
        heading_level:     0 for preamble, 1-6 for h1-h6.
        content:           Full raw Markdown for this section.
        chunk_index:       0-based position within the document.
        heading_hierarchy: List of ancestor headings from root to this chunk.
        token_count:       Estimated token count for this chunk's content.
    """

    heading: str
    heading_level: int
    content: str
    chunk_index: int
    heading_hierarchy: list[str] = field(default_factory=list)
    token_count: int = 0


def _build_heading_hierarchy(
    boundaries: list[tuple[int, str, int]],
    current_idx: int,
) -> list[str]:
    """Build the heading hierarchy for a chunk at current_idx.

    Walks backward from current_idx to collect the nearest ancestor at each
    lower heading level. E.g., for an h3, collects the nearest h2 and h1.
    """
    if current_idx < 0 or current_idx >= len(boundaries):
        return []

    _, current_heading, current_level = boundaries[current_idx]
    if current_level <= 1:
        return [current_heading] if current_heading else []

    ancestors: list[str] = []
    seen_levels: set[int] = set()
    for j in range(current_idx - 1, -1, -1):
        _, ancestor_heading, ancestor_level = boundaries[j]
        if ancestor_level < current_level and ancestor_level not in seen_levels:
            ancestors.append(ancestor_heading)
            seen_levels.add(ancestor_level)
            if ancestor_level == 1:
                break

    ancestors.reverse()
    if current_heading:
        ancestors.append(current_heading)
    return ancestors


def _is_fence_opener(line: str) -> bool:
    """Return True if *line* starts a fenced code block (3+ backticks at start).

    Lines like '```python' or '````' are openers.
    A backtick sequence that appears mid-line (after other chars) is NOT an opener.
    """
    stripped = line.lstrip()
    return stripped.startswith("```") and (
        len(stripped) == 3 or not stripped[3].strip() or stripped[3].isalpha()
    )


def _is_fence_closer(line: str) -> bool:
    """Return True if *line* is a closing fence (exactly 3+ backticks, nothing else)."""
    stripped = line.strip()
    return len(stripped) >= 3 and all(c == "`" for c in stripped)


def _merge_atomic_blocks(paragraphs: list[str]) -> list[str]:
    """Merge paragraphs that belong to the same atomic block.

    Atomic blocks that must never be split:
    - Fenced code blocks (``` ... ```) — possibly containing blank lines.
    - Markdown tables (consecutive paragraphs whose lines start with '|').

    Algorithm:
    1. Iterate through paragraphs (split on ``\\n\\n``).
    2. Track ``in_code_fence`` state via fence openers/closers.
    3. While inside a fence, accumulate paragraphs (rejoin with ``\\n\\n``).
    4. For table lines (lines starting with ``|``), merge consecutive table paragraphs.
    """
    if not paragraphs:
        return paragraphs

    merged: list[str] = []
    in_code_fence = False
    current_block: list[str] = []

    def _is_table_paragraph(para: str) -> bool:
        """Return True if every non-empty line in the paragraph starts with '|'."""
        lines = para.splitlines()
        non_empty = [ln for ln in lines if ln.strip()]
        return bool(non_empty) and all(ln.lstrip().startswith("|") for ln in non_empty)

    def _para_toggles_fence(para: str) -> tuple[bool, bool]:
        """Return (opens_fence, closes_fence) for a paragraph.

        Scans each line for fence markers, tracking state.
        Returns the state of in_code_fence before and after processing the paragraph.
        """
        state = False
        opened = False
        closed = False
        for line in para.splitlines():
            if not state and _is_fence_opener(line):
                state = True
                opened = True
            elif state and _is_fence_closer(line):
                state = False
                closed = True
        return opened, closed

    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]

        if in_code_fence:
            # Inside a fence — accumulate unconditionally
            current_block.append(para)
            # Check if this paragraph closes the fence
            _, closes = _para_toggles_fence(para)
            if closes:
                in_code_fence = False
                merged.append("\n\n".join(current_block))
                current_block = []
            i += 1
            continue

        # Check if this paragraph opens a fence
        opens, closes = _para_toggles_fence(para)
        if opens and not closes:
            # Fence opens but does not close in this paragraph — start accumulating
            in_code_fence = True
            current_block = [para]
            i += 1
            continue
        if opens and closes:
            # Fence opens and closes in the same paragraph — atomic, emit directly
            merged.append(para)
            i += 1
            continue

        # Check if this is a table paragraph
        if _is_table_paragraph(para):
            # Accumulate consecutive table paragraphs
            table_parts = [para]
            i += 1
            while i < len(paragraphs) and _is_table_paragraph(paragraphs[i]):
                table_parts.append(paragraphs[i])
                i += 1
            merged.append("\n\n".join(table_parts))
            continue

        # Regular paragraph — emit as-is
        merged.append(para)
        i += 1

    # Unclosed fence (defensive): flush whatever was accumulated
    if current_block:
        merged.append("\n\n".join(current_block))

    return merged


def _sub_chunk_by_paragraphs(
    content: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    """Split a large section into sub-chunks at paragraph boundaries.

    Splits at double-newline boundaries. If a single paragraph exceeds
    max_chars, it is kept as-is (no mid-sentence splitting).
    Adds overlap from the end of the previous chunk to the start of the next.

    Atomic blocks (code fences, tables) are never split — see _merge_atomic_blocks.
    """
    if len(content) <= max_chars:
        return [content]

    paragraphs = _merge_atomic_blocks(content.split("\n\n"))
    sub_chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        # If adding this paragraph would exceed max, flush current
        if current_parts and current_len + para_len + 2 > max_chars:
            sub_chunks.append("\n\n".join(current_parts))
            # Overlap: carry tail of previous chunk
            if overlap_chars > 0:
                tail = current_parts[-1]
                overlap_text = tail[-overlap_chars:] if len(tail) > overlap_chars else tail
                current_parts = [overlap_text, para]
                current_len = len(overlap_text) + para_len + 2
            else:
                current_parts = [para]
                current_len = para_len
        else:
            current_parts.append(para)
            current_len += para_len + (2 if current_parts else 0)

    if current_parts:
        sub_chunks.append("\n\n".join(current_parts))

    return sub_chunks if sub_chunks else [content]


def _compute_max_chunks(markdown_len: int) -> int:
    """Compute dynamic max chunks based on document size.

    Returns at least _DEFAULT_MAX_CHUNKS, scales up by _DYNAMIC_CHUNKS_PER_KB.
    """
    dynamic = max(_DEFAULT_MAX_CHUNKS, (markdown_len // 1024) * _DYNAMIC_CHUNKS_PER_KB)
    # Hard cap at 100 to prevent runaway
    return min(dynamic, 100)


def chunk_markdown_by_headings(
    markdown: str,
    *,
    min_chunk_chars: int = 0,
    max_chunk_chars: int = _DEFAULT_MAX_CHUNK_CHARS,
    overlap_chars: int = _DEFAULT_OVERLAP_CHARS,
    enrich_hierarchy: bool = True,
) -> list[MarkdownChunk]:
    """Split a Markdown string into chunks at heading boundaries.

    Uses the markdown-it-py token stream so that headings inside fenced code
    blocks are never treated as section boundaries.

    Args:
        markdown:          Raw Markdown text.
        min_chunk_chars:   Chunks whose body is shorter than this are merged
                           into the preceding chunk. Defaults to 0 (no merging).
        max_chunk_chars:   Maximum chars per chunk. Oversized sections are
                           recursively sub-chunked at paragraph boundaries.
                           Defaults to 2000.
        overlap_chars:     Characters of overlap between consecutive sub-chunks
                           for context continuity. Defaults to 100.
        enrich_hierarchy:  If True, each chunk includes its heading hierarchy
                           (ancestor headings) for better embedding context.

    Returns:
        Ordered list of MarkdownChunk objects. Empty list for empty input.
        A document with no headings returns a single chunk with heading="" and
        heading_level=0.
    """
    if not markdown.strip():
        return []

    lines = markdown.splitlines(keepends=True)
    tokens = _MD.parse(markdown)

    # Collect heading boundaries
    boundaries: list[tuple[int, str, int]] = []
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.map:
            level = int(token.tag[1])
            inline_token = tokens[i + 1] if i + 1 < len(tokens) else None
            heading_text = inline_token.content if inline_token else ""
            boundaries.append((token.map[0], heading_text, level))

    if not boundaries:
        sub_chunks = _sub_chunk_by_paragraphs(markdown, max_chunk_chars, overlap_chars)
        return [
            MarkdownChunk(
                heading="",
                heading_level=0,
                content=sc,
                chunk_index=i,
                heading_hierarchy=[],
                token_count=_count_tokens(sc),
            )
            for i, sc in enumerate(sub_chunks)
        ]

    # Build raw chunks by slicing source lines between boundaries
    raw_chunks: list[tuple[str, str, int, int]] = []  # (heading, content, level, boundary_idx)

    first_boundary_line = boundaries[0][0]
    if first_boundary_line > 0:
        preamble = "".join(lines[:first_boundary_line])
        if preamble.strip():
            raw_chunks.append(("", preamble, 0, -1))

    for idx, (start_line, heading_text, level) in enumerate(boundaries):
        end_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        content = "".join(lines[start_line:end_line])
        raw_chunks.append((heading_text, content, level, idx))

    # Merge chunks whose body is below the threshold
    def _body_length(content: str) -> int:
        body_lines = content.splitlines()
        body = "\n".join(line for line in body_lines if not line.startswith("#")).strip()
        return len(body)

    merged: list[tuple[str, str, int, int]] = []
    for heading, content, level, bidx in raw_chunks:
        if (
            min_chunk_chars > 0
            and merged
            and level != 0
            and _body_length(content) < min_chunk_chars
        ):
            prev_heading, prev_content, prev_level, prev_bidx = merged[-1]
            merged[-1] = (prev_heading, prev_content + content, prev_level, prev_bidx)
        else:
            merged.append((heading, content, level, bidx))

    # Dynamic max chunks based on document size
    max_chunks = _compute_max_chunks(len(markdown))

    if len(merged) > max_chunks:
        overflow = merged[max_chunks - 1 :]
        combined_content = "".join(c for _, c, _, _ in overflow)
        heading, _, level, bidx = merged[max_chunks - 1]
        merged = [*merged[: max_chunks - 1], (heading, combined_content, level, bidx)]

    # Build final chunks with sub-chunking, hierarchy, and token counts
    result: list[MarkdownChunk] = []
    chunk_idx = 0

    for heading, content, level, bidx in merged:
        hierarchy = (
            _build_heading_hierarchy(boundaries, bidx) if enrich_hierarchy and bidx >= 0 else []
        )

        # Sub-chunk oversized sections
        sub_chunks = _sub_chunk_by_paragraphs(content, max_chunk_chars, overlap_chars)

        for sc_i, sc_content in enumerate(sub_chunks):
            # Enrich: prepend hierarchy context to sub-chunks (except first)
            enriched_content = sc_content
            if enrich_hierarchy and hierarchy and sc_i > 0:
                hierarchy_prefix = " > ".join(hierarchy)
                enriched_content = f"[Context: {hierarchy_prefix}]\n\n{sc_content}"

            result.append(
                MarkdownChunk(
                    heading=heading if sc_i == 0 else f"{heading} (part {sc_i + 1})",
                    heading_level=level,
                    content=enriched_content,
                    chunk_index=chunk_idx,
                    heading_hierarchy=hierarchy,
                    token_count=_count_tokens(enriched_content),
                )
            )
            chunk_idx += 1

    return result
