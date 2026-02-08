"""Human-readable block reference mapping (¶N notation).

Maps opaque block UUIDs to short ¶N references so the AI agent never
sees or exposes raw UUIDs to users. The map is built per-conversation-turn
from the current TipTap document and passed to MCP tool handlers.

Usage:
    ref_map = BlockRefMap.from_tiptap(note_content)
    ref_map.to_ref("e37ebdcb-...")   # → "¶3"
    ref_map.to_id("¶3")             # → "e37ebdcb-..."
    ref_map.resolve("¶3")           # → "e37ebdcb-..." (accepts either format)
"""

from __future__ import annotations

import re
from typing import Any

# Regex to detect ¶N references in text
_PILCROW_REF_RE = re.compile(r"¶(\d+)")


class BlockRefMap:
    """Bidirectional mapping between ¶N block references and block UUIDs."""

    __slots__ = ("_id_to_ref", "_ref_to_id", "_ref_to_preview")

    def __init__(self) -> None:
        self._ref_to_id: dict[str, str] = {}
        self._id_to_ref: dict[str, str] = {}
        self._ref_to_preview: dict[str, str] = {}

    @classmethod
    def from_tiptap(cls, content: dict[str, Any]) -> BlockRefMap:
        """Build a reference map from a TipTap JSON document.

        Assigns sequential ¶1, ¶2, ... to each block that has an ID.
        Extracts the first 8 words of each block as a content preview.

        Args:
            content: TipTap document root (type: "doc").

        Returns:
            Populated BlockRefMap instance.
        """
        instance = cls()
        if content.get("type") != "doc":
            return instance

        nodes: list[dict[str, Any]] = content.get("content", [])
        counter = 0
        for node in nodes:
            block_id = _get_block_id(node)
            if not block_id:
                continue
            counter += 1
            ref = f"¶{counter}"
            preview = _extract_preview(node, max_words=8)
            instance._ref_to_id[ref] = block_id
            instance._id_to_ref[block_id] = ref
            instance._ref_to_preview[ref] = preview

        return instance

    # ------------------------------------------------------------------
    # Lookup methods
    # ------------------------------------------------------------------

    def to_ref(self, block_id: str) -> str:
        """Convert block UUID to ¶N reference.

        Returns the original block_id if not found in the map.
        """
        return self._id_to_ref.get(block_id, block_id)

    def to_id(self, ref: str) -> str:
        """Convert ¶N reference to block UUID.

        Returns the original ref if not found in the map.
        """
        return self._ref_to_id.get(ref, ref)

    def resolve(self, value: str) -> str:
        """Resolve either a ¶N reference or a UUID to the underlying UUID.

        Accepts both formats — useful for tool inputs where the AI
        may send either notation.
        """
        if value.startswith("¶"):
            return self._ref_to_id.get(value, value)
        return value

    def get_preview(self, ref_or_id: str) -> str:
        """Get content preview for a block reference or UUID."""
        ref = ref_or_id if ref_or_id.startswith("¶") else self._id_to_ref.get(ref_or_id, "")
        return self._ref_to_preview.get(ref, "")

    def format_ref(self, block_id: str) -> str:
        """Format a block UUID as a human-readable reference with preview.

        Example: '¶3 "Design GraphQL schema for complex"'
        """
        ref = self.to_ref(block_id)
        preview = self._ref_to_preview.get(ref, "")
        if preview:
            return f'¶{ref[1:]} "{preview}"' if ref.startswith("¶") else block_id
        return ref

    def resolve_ids_in_text(self, text: str) -> str:
        """Replace all ¶N references in text with their UUIDs."""

        def _replace(match: re.Match[str]) -> str:
            ref = f"¶{match.group(1)}"
            return self._ref_to_id.get(ref, ref)

        return _PILCROW_REF_RE.sub(_replace, text)

    def replace_ids_in_text(self, text: str) -> str:
        """Replace all block UUIDs in text with ¶N references."""
        result = text
        for block_id, ref in self._id_to_ref.items():
            result = result.replace(block_id, ref)
        return result

    @property
    def is_empty(self) -> bool:
        """Check if the map contains any block references."""
        return len(self._ref_to_id) == 0

    def __len__(self) -> int:
        return len(self._ref_to_id)

    def __contains__(self, key: str) -> bool:
        return key in self._ref_to_id or key in self._id_to_ref


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _get_block_id(node: dict[str, Any]) -> str | None:
    """Extract block ID from TipTap node attrs."""
    attrs = node.get("attrs")
    if not attrs:
        return None
    return attrs.get("id") or attrs.get("blockId") or None


def _extract_preview(node: dict[str, Any], *, max_words: int = 8) -> str:
    """Extract the first N words from a block node's text content."""
    text = _node_text(node)
    if not text:
        return ""
    words = text.split()[:max_words]
    preview = " ".join(words)
    if len(text.split()) > max_words:
        preview += "…"
    return preview


def _node_text(node: dict[str, Any]) -> str:
    """Recursively extract all text from a TipTap node."""
    parts: list[str] = []
    node_type = node.get("type", "")

    # For headings, include the heading prefix for context
    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        parts.append("#" * level)

    for child in node.get("content", []):
        if child.get("type") == "text":
            parts.append(child.get("text", ""))
        elif child.get("type") == "inlineIssue":
            key = child.get("attrs", {}).get("issueKey", "")
            if key:
                parts.append(f"[{key}]")
        elif child.get("type") == "hardBreak":
            parts.append(" ")
        else:
            inner = _node_text(child)
            if inner:
                parts.append(inner)

    return " ".join(parts).strip()
