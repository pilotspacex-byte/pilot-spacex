"""VersionDigestService — AI-powered change digest with caching.

Compares a version to its predecessor, calls Claude Sonnet for a
human-readable change summary, and caches the result in the digest column.
Target: <3s for 95% of requests (FR-040).

Feature 017: Note Versioning — Sprint 1 (T-210)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.domain.exceptions import NotFoundError
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DigestResult:
    """Result of digest generation."""

    version_id: UUID
    digest: str
    from_cache: bool


class VersionDigestService:
    """Generates and caches an AI change digest for a note version.

    If a cached digest exists, returns it directly (cache-first).
    Otherwise, fetches the previous version, calls the LLM, and caches.
    """

    def __init__(
        self,
        session: AsyncSession,
        version_repo: NoteVersionRepository,
        anthropic_api_key: str | None = None,
    ) -> None:
        self._session = session
        self._version_repo = version_repo
        self._anthropic_api_key = anthropic_api_key

    async def execute(
        self,
        version_id: UUID,
        note_id: UUID,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> DigestResult:
        """Return (or generate) a digest for a version.

        Args:
            version_id: Target version UUID.
            note_id: Parent note UUID.
            workspace_id: Workspace UUID.
            user_id: Caller user UUID for cost attribution (None for background jobs).

        Returns:
            DigestResult with the digest text and cache status.

        Raises:
            ValueError: If version not found.
        """
        version = await self._version_repo.get_by_id_for_note(version_id, note_id, workspace_id)
        if not version:
            msg = f"Version {version_id} not found for note {note_id}"
            raise NotFoundError(msg)

        # Cache-first: return if already computed
        if version.digest is not None:
            return DigestResult(
                version_id=version_id,
                digest=version.digest,
                from_cache=True,
            )

        # Find the previous version for comparison
        all_versions = await self._version_repo.list_by_note(
            note_id, workspace_id, limit=100, offset=0
        )
        previous = _find_previous_version(version_id, list(all_versions))

        digest = await self._generate_digest(version.content, previous, workspace_id, user_id)

        # Persist digest cache in DB
        from pilot_space.infrastructure.database.models.note_version import NoteVersion as NVModel

        await self._session.execute(
            __import__("sqlalchemy", fromlist=["text", "update"])
            .update(NVModel)
            .where(NVModel.id == version_id)
            .values(
                digest=digest,
                digest_cached_at=__import__("sqlalchemy", fromlist=["func"]).func.now(),
            )
        )
        await self._session.flush()

        return DigestResult(version_id=version_id, digest=digest, from_cache=False)

    async def _generate_digest(
        self,
        new_content: dict[str, Any],
        previous_content: dict[str, Any] | None,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> str:
        """Call Claude Sonnet to generate a change summary.

        Falls back to a minimal description when the API key is unavailable.

        Args:
            new_content: TipTap JSON for the new version.
            previous_content: TipTap JSON for the previous version (or None if first).
            workspace_id: Workspace UUID for cost tracking.
            user_id: Caller user UUID for cost attribution.

        Returns:
            Human-readable change summary (1-3 sentences).
        """
        if not self._anthropic_api_key:
            return self._minimal_digest(new_content, previous_content)

        try:
            import anthropic  # type: ignore[import-untyped]

            from pilot_space.ai.infrastructure.cost_tracker import (
                extract_response_usage,
                track_cost,
            )

            client = anthropic.AsyncAnthropic(api_key=self._anthropic_api_key)

            new_text = _tiptap_to_text(new_content)
            prev_text = (
                _tiptap_to_text(previous_content) if previous_content else "(no previous version)"
            )

            prompt = (
                "You are summarizing changes between two versions of a note.\n\n"
                f"Previous version:\n{prev_text[:2000]}\n\n"
                f"New version:\n{new_text[:2000]}\n\n"
                "Summarize the key changes in 1-3 sentences. "
                "Be concise and specific. Focus on what was added, removed, or modified."
            )

            _model = "claude-sonnet-4-20250514"
            message = await client.messages.create(
                model=_model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            input_tokens, output_tokens = extract_response_usage(message)

            if workspace_id is not None and (input_tokens or output_tokens):
                await track_cost(
                    self._session,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    agent_name="version_digest",
                    provider="anthropic",
                    model=_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    operation_type="version_digest",
                )

            content = message.content[0]
            if hasattr(content, "text"):
                return content.text.strip()  # type: ignore[union-attr]
            return self._minimal_digest(new_content, previous_content)

        except Exception:
            return self._minimal_digest(new_content, previous_content)

    @staticmethod
    def _minimal_digest(
        new_content: dict[str, Any], previous_content: dict[str, Any] | None
    ) -> str:
        """Generate a minimal digest without AI when API unavailable."""
        new_blocks = len(new_content.get("content", []))
        if previous_content is None:
            return f"Initial version with {new_blocks} block(s)."
        old_blocks = len(previous_content.get("content", []))
        delta = new_blocks - old_blocks
        if delta == 0:
            return "Content updated."
        direction = "added" if delta > 0 else "removed"
        return f"{abs(delta)} block(s) {direction}. Total: {new_blocks} blocks."


def _find_previous_version(
    target_id: UUID,
    versions: list[Any],
) -> dict[str, Any] | None:
    """Find the content of the version immediately before target_id.

    Versions are ordered newest first.

    Args:
        target_id: The version we are generating a digest for.
        versions: All versions for the note, newest first.

    Returns:
        Content dict of the preceding version, or None if target is first.
    """
    for idx, v in enumerate(versions):
        if str(v.id) == str(target_id):
            if idx + 1 < len(versions):
                return versions[idx + 1].content
            return None
    return None


def _tiptap_to_text(content: dict[str, Any]) -> str:
    """Extract plain text from TipTap JSON for LLM context."""
    parts: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        for child in node.get("content", []):
            walk(child)
        if node.get("type") in ("paragraph", "heading", "listItem"):
            parts.append("\n")

    walk(content)
    return "".join(parts).strip()
