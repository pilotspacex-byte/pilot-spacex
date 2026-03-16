"""ImpactAnalysisService — scan version content for entity references.

Identifies PS-42 style issue references, note links, and other entity mentions
in a version's TipTap content. Target: >90% accuracy (FR-041).

Feature 017: Note Versioning — Sprint 1 (T-211)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Matches PS-123 style issue identifiers
_ISSUE_REF_PATTERN = re.compile(r"\b([A-Z]{1,10}-\d+)\b")
# Matches UUID references (note links etc.)
_UUID_PATTERN = re.compile(
    r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
    re.IGNORECASE,
)


class ReferenceType(StrEnum):
    """Type of entity reference found in version content."""

    ISSUE = "issue"
    NOTE = "note"
    UNKNOWN = "unknown"


@dataclass
class EntityReference:
    """A detected entity reference in note content."""

    reference_type: ReferenceType
    identifier: str
    raw_text: str


@dataclass
class ImpactResult:
    """Result of impact analysis for a version."""

    version_id: UUID
    references: list[EntityReference]

    @property
    def issue_references(self) -> list[EntityReference]:
        return [r for r in self.references if r.reference_type == ReferenceType.ISSUE]

    @property
    def note_references(self) -> list[EntityReference]:
        return [r for r in self.references if r.reference_type == ReferenceType.NOTE]


class ImpactAnalysisService:
    """Scans version content for entity references.

    Detects:
    - Issue identifiers (PS-42 pattern): letter prefix + hyphen + number
    - UUID references (potential note or other entity links)
    """

    def __init__(
        self,
        session: AsyncSession,
        version_repo: NoteVersionRepository,
    ) -> None:
        self._session = session
        self._version_repo = version_repo

    async def execute(
        self,
        version_id: UUID,
        note_id: UUID,
        workspace_id: UUID,
    ) -> ImpactResult:
        """Scan a version's content for entity references.

        Args:
            version_id: Target version UUID.
            note_id: Parent note UUID.
            workspace_id: Workspace UUID.

        Returns:
            ImpactResult with all detected references.

        Raises:
            ValueError: If version not found.
        """
        version = await self._version_repo.get_by_id_for_note(version_id, note_id, workspace_id)
        if not version:
            msg = f"Version {version_id} not found for note {note_id}"
            raise ValueError(msg)

        text = _extract_text_from_tiptap(version.content)
        refs = _detect_references(text)

        return ImpactResult(version_id=version_id, references=refs)


def _extract_text_from_tiptap(content: dict[str, Any]) -> str:
    """Recursively extract plain text from a TipTap document."""
    parts: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        # Also scan node attributes for data-id etc.
        attrs = node.get("attrs") or {}
        for val in attrs.values():
            if isinstance(val, str):
                parts.append(f" {val} ")
        for child in node.get("content", []):
            walk(child)

    walk(content)
    return " ".join(parts)


def _detect_references(text: str) -> list[EntityReference]:
    """Detect all entity references in plain text."""
    refs: list[EntityReference] = []
    seen: set[str] = set()

    for match in _ISSUE_REF_PATTERN.finditer(text):
        identifier = match.group(1)
        if identifier not in seen:
            seen.add(identifier)
            refs.append(
                EntityReference(
                    reference_type=ReferenceType.ISSUE,
                    identifier=identifier,
                    raw_text=match.group(0),
                )
            )

    for match in _UUID_PATTERN.finditer(text):
        identifier = match.group(1).lower()
        if identifier not in seen:
            seen.add(identifier)
            refs.append(
                EntityReference(
                    reference_type=ReferenceType.NOTE,
                    identifier=identifier,
                    raw_text=match.group(0),
                )
            )

    return refs
