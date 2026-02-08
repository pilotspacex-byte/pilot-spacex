"""Tests for BlockRefMap (¶N block reference notation).

Verifies the bidirectional mapping between ¶N human-readable references
and block UUIDs, including TipTap document parsing and text replacement.
"""

from __future__ import annotations

import pytest

from pilot_space.ai.mcp.block_ref_map import BlockRefMap

# ------------------------------------------------------------------
# Fixtures: sample TipTap documents
# ------------------------------------------------------------------

TIPTAP_DOC = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 1, "blockId": "uuid-heading-1"},
            "content": [{"type": "text", "text": "Architecture Overview"}],
        },
        {
            "type": "paragraph",
            "attrs": {"blockId": "uuid-para-1"},
            "content": [
                {"type": "text", "text": "This document describes the system architecture."}
            ],
        },
        {
            "type": "heading",
            "attrs": {"level": 2, "blockId": "uuid-heading-2"},
            "content": [{"type": "text", "text": "Database Design"}],
        },
        {
            "type": "paragraph",
            "attrs": {"blockId": "uuid-para-2"},
            "content": [
                {"type": "text", "text": "We use PostgreSQL with "},
                {"type": "text", "text": "pgvector", "marks": [{"type": "bold"}]},
                {"type": "text", "text": " for embeddings."},
            ],
        },
        {
            "type": "codeBlock",
            "attrs": {"language": "sql", "blockId": "uuid-code-1"},
            "content": [{"type": "text", "text": "SELECT * FROM issues;"}],
        },
    ],
}

TIPTAP_EMPTY = {"type": "doc", "content": []}

TIPTAP_NO_IDS = {
    "type": "doc",
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "No ID here"}]},
    ],
}

TIPTAP_MIXED_IDS = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "attrs": {"id": "alt-id-1"},
            "content": [{"type": "text", "text": "Uses id attr"}],
        },
        {
            "type": "paragraph",
            "attrs": {"blockId": "block-id-2"},
            "content": [{"type": "text", "text": "Uses blockId attr"}],
        },
    ],
}


# ------------------------------------------------------------------
# Construction tests
# ------------------------------------------------------------------


class TestFromTiptap:
    def test_builds_from_document(self) -> None:
        ref_map = BlockRefMap.from_tiptap(TIPTAP_DOC)
        assert len(ref_map) == 5
        assert not ref_map.is_empty

    def test_sequential_numbering(self) -> None:
        ref_map = BlockRefMap.from_tiptap(TIPTAP_DOC)
        assert ref_map.to_ref("uuid-heading-1") == "¶1"
        assert ref_map.to_ref("uuid-para-1") == "¶2"
        assert ref_map.to_ref("uuid-heading-2") == "¶3"
        assert ref_map.to_ref("uuid-para-2") == "¶4"
        assert ref_map.to_ref("uuid-code-1") == "¶5"

    def test_empty_document(self) -> None:
        ref_map = BlockRefMap.from_tiptap(TIPTAP_EMPTY)
        assert len(ref_map) == 0
        assert ref_map.is_empty

    def test_non_doc_type(self) -> None:
        ref_map = BlockRefMap.from_tiptap({"type": "paragraph"})
        assert ref_map.is_empty

    def test_nodes_without_ids_skipped(self) -> None:
        ref_map = BlockRefMap.from_tiptap(TIPTAP_NO_IDS)
        assert len(ref_map) == 0

    def test_mixed_id_attrs(self) -> None:
        ref_map = BlockRefMap.from_tiptap(TIPTAP_MIXED_IDS)
        assert len(ref_map) == 2
        assert ref_map.to_ref("alt-id-1") == "¶1"
        assert ref_map.to_ref("block-id-2") == "¶2"


# ------------------------------------------------------------------
# Lookup tests
# ------------------------------------------------------------------


class TestLookup:
    @pytest.fixture
    def ref_map(self) -> BlockRefMap:
        return BlockRefMap.from_tiptap(TIPTAP_DOC)

    def test_to_ref(self, ref_map: BlockRefMap) -> None:
        assert ref_map.to_ref("uuid-para-1") == "¶2"

    def test_to_ref_unknown_returns_original(self, ref_map: BlockRefMap) -> None:
        assert ref_map.to_ref("unknown-uuid") == "unknown-uuid"

    def test_to_id(self, ref_map: BlockRefMap) -> None:
        assert ref_map.to_id("¶2") == "uuid-para-1"

    def test_to_id_unknown_returns_original(self, ref_map: BlockRefMap) -> None:
        assert ref_map.to_id("¶99") == "¶99"

    def test_resolve_pilcrow_ref(self, ref_map: BlockRefMap) -> None:
        assert ref_map.resolve("¶3") == "uuid-heading-2"

    def test_resolve_uuid_passthrough(self, ref_map: BlockRefMap) -> None:
        assert ref_map.resolve("uuid-para-1") == "uuid-para-1"

    def test_resolve_unknown_ref_returns_original(self, ref_map: BlockRefMap) -> None:
        assert ref_map.resolve("¶99") == "¶99"

    def test_contains_ref(self, ref_map: BlockRefMap) -> None:
        assert "¶1" in ref_map
        assert "¶5" in ref_map
        assert "¶99" not in ref_map

    def test_contains_uuid(self, ref_map: BlockRefMap) -> None:
        assert "uuid-heading-1" in ref_map
        assert "unknown-uuid" not in ref_map


# ------------------------------------------------------------------
# Preview tests
# ------------------------------------------------------------------


class TestPreview:
    @pytest.fixture
    def ref_map(self) -> BlockRefMap:
        return BlockRefMap.from_tiptap(TIPTAP_DOC)

    def test_get_preview_by_ref(self, ref_map: BlockRefMap) -> None:
        preview = ref_map.get_preview("¶1")
        assert "Architecture Overview" in preview

    def test_get_preview_by_uuid(self, ref_map: BlockRefMap) -> None:
        preview = ref_map.get_preview("uuid-heading-1")
        assert "Architecture Overview" in preview

    def test_get_preview_unknown(self, ref_map: BlockRefMap) -> None:
        assert ref_map.get_preview("unknown") == ""

    def test_format_ref(self, ref_map: BlockRefMap) -> None:
        formatted = ref_map.format_ref("uuid-heading-1")
        assert formatted.startswith("¶1")
        assert "Architecture Overview" in formatted

    def test_format_ref_unknown(self, ref_map: BlockRefMap) -> None:
        assert ref_map.format_ref("unknown-uuid") == "unknown-uuid"

    def test_heading_prefix_in_preview(self, ref_map: BlockRefMap) -> None:
        preview = ref_map.get_preview("¶1")
        assert preview.startswith("#")

    def test_long_text_truncated(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"blockId": "long-block"},
                    "content": [{"type": "text", "text": " ".join(f"word{i}" for i in range(20))}],
                }
            ],
        }
        ref_map = BlockRefMap.from_tiptap(doc)
        preview = ref_map.get_preview("¶1")
        assert preview.endswith("…")
        assert len(preview.split()) <= 9  # 8 words + ellipsis


# ------------------------------------------------------------------
# Text replacement tests
# ------------------------------------------------------------------


class TestTextReplacement:
    @pytest.fixture
    def ref_map(self) -> BlockRefMap:
        return BlockRefMap.from_tiptap(TIPTAP_DOC)

    def test_resolve_ids_in_text(self, ref_map: BlockRefMap) -> None:
        text = "Updated blocks ¶1 and ¶3 successfully."
        result = ref_map.resolve_ids_in_text(text)
        assert "uuid-heading-1" in result
        assert "uuid-heading-2" in result
        assert "¶" not in result

    def test_resolve_ids_unknown_ref_kept(self, ref_map: BlockRefMap) -> None:
        text = "Block ¶99 not found."
        result = ref_map.resolve_ids_in_text(text)
        assert "¶99" in result

    def test_replace_ids_in_text(self, ref_map: BlockRefMap) -> None:
        text = "Source: uuid-heading-1, target: uuid-para-2"
        result = ref_map.replace_ids_in_text(text)
        assert "¶1" in result
        assert "¶4" in result
        assert "uuid-heading-1" not in result
        assert "uuid-para-2" not in result

    def test_replace_ids_no_match(self, ref_map: BlockRefMap) -> None:
        text = "No UUIDs here."
        assert ref_map.replace_ids_in_text(text) == text


# ------------------------------------------------------------------
# Integration: ContentConverter + BlockRefMap
# ------------------------------------------------------------------


class TestContentConverterIntegration:
    def test_tiptap_to_markdown_with_ref_map(self) -> None:
        from pilot_space.application.services.note.content_converter import ContentConverter

        ref_map = BlockRefMap.from_tiptap(TIPTAP_DOC)
        converter = ContentConverter()
        md = converter.tiptap_to_markdown(TIPTAP_DOC, block_ref_map=ref_map)

        # Should contain ¶N references, not <!-- block:uuid --> comments
        assert "[¶1]" in md
        assert "[¶2]" in md
        assert "[¶3]" in md
        assert "<!-- block:" not in md

    def test_tiptap_to_markdown_without_ref_map(self) -> None:
        from pilot_space.application.services.note.content_converter import ContentConverter

        converter = ContentConverter()
        md = converter.tiptap_to_markdown(TIPTAP_DOC)

        # Should use legacy <!-- block:uuid --> format
        assert "<!-- block:uuid-heading-1 -->" in md
        assert "[¶" not in md

    def test_markdown_content_preserved(self) -> None:
        from pilot_space.application.services.note.content_converter import ContentConverter

        ref_map = BlockRefMap.from_tiptap(TIPTAP_DOC)
        converter = ContentConverter()
        md = converter.tiptap_to_markdown(TIPTAP_DOC, block_ref_map=ref_map)

        assert "Architecture Overview" in md
        assert "Database Design" in md
        assert "PostgreSQL" in md
        assert "SELECT * FROM issues;" in md


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_inline_issue_in_preview(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"blockId": "issue-block"},
                    "content": [
                        {"type": "text", "text": "Fix "},
                        {
                            "type": "inlineIssue",
                            "attrs": {"issueKey": "PS-42", "issueId": "abc"},
                        },
                        {"type": "text", "text": " before release"},
                    ],
                }
            ],
        }
        ref_map = BlockRefMap.from_tiptap(doc)
        preview = ref_map.get_preview("¶1")
        assert "[PS-42]" in preview

    def test_hard_break_in_preview(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"blockId": "break-block"},
                    "content": [
                        {"type": "text", "text": "Line one"},
                        {"type": "hardBreak"},
                        {"type": "text", "text": "Line two"},
                    ],
                }
            ],
        }
        ref_map = BlockRefMap.from_tiptap(doc)
        preview = ref_map.get_preview("¶1")
        assert "Line one" in preview
        assert "Line two" in preview

    def test_empty_text_block(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"blockId": "empty-block"},
                    "content": [],
                }
            ],
        }
        ref_map = BlockRefMap.from_tiptap(doc)
        assert len(ref_map) == 1
        assert ref_map.get_preview("¶1") == ""
