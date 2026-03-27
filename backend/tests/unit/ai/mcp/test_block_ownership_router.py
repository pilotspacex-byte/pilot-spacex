"""Unit tests for block ownership router helpers (T-115, Feature 016 M6b).

Tests the _find_block, _remove_block, and business logic of
the block approve/reject API without requiring a full HTTP stack.
"""

from __future__ import annotations

from pilot_space.application.services.block_ownership import BlockOwnershipService

_find_block = BlockOwnershipService._find_block
_remove_block = BlockOwnershipService._remove_block


class TestFindBlock:
    def test_finds_top_level_block(self):
        blocks = [{"attrs": {"id": "block-1"}, "type": "paragraph"}]
        result = _find_block(blocks, "block-1")
        assert result is not None
        assert result["attrs"]["id"] == "block-1"

    def test_returns_none_when_not_found(self):
        blocks = [{"attrs": {"id": "block-1"}, "type": "paragraph"}]
        result = _find_block(blocks, "block-999")
        assert result is None

    def test_finds_nested_block(self):
        blocks = [
            {
                "type": "bulletList",
                "attrs": {"id": "list-1"},
                "content": [
                    {"type": "listItem", "attrs": {"id": "item-1"}},
                ],
            }
        ]
        result = _find_block(blocks, "item-1")
        assert result is not None
        assert result["attrs"]["id"] == "item-1"

    def test_handles_empty_blocks(self):
        result = _find_block([], "block-1")
        assert result is None

    def test_handles_block_without_attrs(self):
        blocks = [{"type": "paragraph"}]
        result = _find_block(blocks, "block-1")
        assert result is None

    def test_handles_block_without_id(self):
        blocks = [{"type": "paragraph", "attrs": {}}]
        result = _find_block(blocks, "block-1")
        assert result is None


class TestRemoveBlock:
    def test_removes_top_level_block(self):
        blocks = [
            {"attrs": {"id": "block-1"}, "type": "paragraph"},
            {"attrs": {"id": "block-2"}, "type": "paragraph"},
        ]
        removed = _remove_block(blocks, "block-1")
        assert removed is True
        assert len(blocks) == 1
        assert blocks[0]["attrs"]["id"] == "block-2"

    def test_returns_false_when_not_found(self):
        blocks = [{"attrs": {"id": "block-1"}, "type": "paragraph"}]
        removed = _remove_block(blocks, "block-999")
        assert removed is False
        assert len(blocks) == 1

    def test_removes_nested_block(self):
        blocks = [
            {
                "type": "bulletList",
                "attrs": {"id": "list-1"},
                "content": [
                    {"type": "listItem", "attrs": {"id": "item-1"}},
                    {"type": "listItem", "attrs": {"id": "item-2"}},
                ],
            }
        ]
        removed = _remove_block(blocks, "item-1")
        assert removed is True
        nested = blocks[0]["content"]
        assert len(nested) == 1
        assert nested[0]["attrs"]["id"] == "item-2"

    def test_handles_empty_blocks(self):
        removed = _remove_block([], "block-1")
        assert removed is False

    def test_removes_last_item_from_list(self):
        blocks = [{"attrs": {"id": "block-1"}, "type": "paragraph"}]
        removed = _remove_block(blocks, "block-1")
        assert removed is True
        assert len(blocks) == 0
