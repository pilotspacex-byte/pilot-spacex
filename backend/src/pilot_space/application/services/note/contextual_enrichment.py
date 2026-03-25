"""Contextual enrichment for markdown chunks using LLM-generated summaries.

Adds a brief context prefix to each chunk, situating it within the full
document. Improves retrieval quality by giving embedding models richer
per-chunk context (the "Contextual Retrieval" technique).

BYOK pattern: if llm_gateway is None, chunks are returned unchanged without
making any API call. All LLM failures degrade gracefully -- original chunks
are preserved on any exception.

Feature 016: Knowledge Graph -- contextual retrieval enrichment.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from pilot_space.application.services.note.markdown_chunker import (
    MarkdownChunk,
)

__all__ = ["enrich_chunks_with_context"]

logger = logging.getLogger(__name__)

# Sentinel user ID for system-initiated enrichment (no real user context)
_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def _estimate_tokens(text: str) -> int:
    """Estimate token count -- 1 token ~ 4 chars for English text."""
    return len(text) // 4


_MAX_CONTEXT_TOKENS = 150
_CONTEXT_ENRICHMENT_TIMEOUT_S = 15.0
_MAX_CONCURRENT_ENRICHMENTS = 4

_CONTEXT_PROMPT_TEMPLATE = """\
Here is the full document:

{full_document}

Here is the chunk:

{chunk_content}

Provide a brief 1-2 sentence context that situates this chunk within the full \
document. Only output the context, nothing else."""


async def _enrich_single_chunk(
    chunk: MarkdownChunk,
    full_document: str,
    llm_gateway: object,
    workspace_id: UUID,
    user_id: UUID,
    content_cap: int,
    semaphore: asyncio.Semaphore,
) -> MarkdownChunk:
    """Enrich a single chunk with an LLM-generated context prefix.

    Returns the original chunk unchanged on any LLM failure.
    Uses semaphore to limit concurrent API calls.
    """
    from pilot_space.ai.providers.provider_selector import TaskType
    from pilot_space.ai.proxy.llm_gateway import LLMGateway

    assert isinstance(llm_gateway, LLMGateway)

    try:
        async with semaphore:
            prompt = _CONTEXT_PROMPT_TEMPLATE.format(
                full_document=full_document[:4000],
                chunk_content=chunk.content[:1000],
            )
            response = await llm_gateway.complete(
                workspace_id=workspace_id,
                user_id=user_id,
                task_type=TaskType.CONTEXTUAL_RETRIEVAL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=_MAX_CONTEXT_TOKENS,
                temperature=0.0,
                agent_name="contextual_enrichment",
            )
            context_text = response.text.strip()
        if not context_text:
            return chunk

        prefix = f"[Context: {context_text}]"
        separator = "\n\n"
        combined = f"{prefix}{separator}{chunk.content}"

        # Truncate context prefix if combined exceeds content_cap
        if len(combined) > content_cap:
            # Reserve space for separator and chunk content
            max_prefix_len = content_cap - len(separator) - len(chunk.content)
            if max_prefix_len <= len("[Context: ]"):
                # Not enough room for even a minimal prefix -- return original
                return chunk
            truncated_context = context_text[: max_prefix_len - len("[Context: ]")]
            prefix = f"[Context: {truncated_context}]"
            combined = f"{prefix}{separator}{chunk.content}"
            combined = combined[:content_cap]

        return MarkdownChunk(
            heading=chunk.heading,
            heading_level=chunk.heading_level,
            content=combined,
            chunk_index=chunk.chunk_index,
            heading_hierarchy=chunk.heading_hierarchy,
            token_count=_estimate_tokens(combined),
        )

    except Exception:
        logger.warning(
            "contextual_enrichment: LLM call failed for chunk %d -- returning original",
            chunk.chunk_index,
            exc_info=True,
        )
        return chunk


async def enrich_chunks_with_context(
    chunks: list[MarkdownChunk],
    full_document: str,
    *,
    llm_gateway: object | None = None,
    workspace_id: UUID | None = None,
    user_id: UUID | None = None,
    api_key: str | None = None,
    content_cap: int = 2000,
) -> list[MarkdownChunk]:
    """Enrich chunks with LLM-generated context summaries.

    For each chunk, calls the LLM via LLMGateway to generate a 1-2 sentence
    context that situates the chunk within the full document. The context
    is prepended as ``[Context: ...]`` before the chunk content.

    Args:
        chunks:        Chunks to enrich (from chunk_markdown_by_headings).
        full_document: Full raw markdown for context generation.
        llm_gateway:   LLMGateway instance. If None, returns chunks unchanged.
        workspace_id:  Workspace UUID for BYOK key lookup.
        user_id:       User UUID. Defaults to system sentinel if None.
        api_key:       Deprecated. Ignored when llm_gateway is provided.
        content_cap:   Maximum character length per enriched chunk (including
                       the context prefix). Defaults to 2000.

    Returns:
        List of MarkdownChunk objects. Unchanged if llm_gateway is None, enriched
        with context prefix otherwise. Individual chunks that fail LLM calls
        are returned unchanged (graceful degradation).
    """
    if llm_gateway is None or not chunks:
        return chunks

    if workspace_id is None:
        return chunks

    effective_user_id = user_id or _SYSTEM_USER_ID
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_ENRICHMENTS)

    tasks = [
        _enrich_single_chunk(
            chunk, full_document, llm_gateway, workspace_id,
            effective_user_id, content_cap, semaphore,
        )
        for chunk in chunks
    ]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=_CONTEXT_ENRICHMENT_TIMEOUT_S,
        )
    except TimeoutError:
        logger.warning(
            "contextual_enrichment: timed out after %.1fs -- returning original chunks",
            _CONTEXT_ENRICHMENT_TIMEOUT_S,
        )
        return chunks

    enriched: list[MarkdownChunk] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.warning(
                "contextual_enrichment: chunk %d raised exception -- returning original: %s",
                i,
                result,
            )
            enriched.append(chunks[i])
        else:
            enriched.append(result)

    return enriched
