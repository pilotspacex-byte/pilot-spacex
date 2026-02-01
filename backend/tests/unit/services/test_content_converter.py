"""TDD tests for ContentConverter — Markdown ↔ TipTap JSONContent conversion.

Tests written FIRST (TDD red phase), implementation follows.
"""

from __future__ import annotations

import uuid

import pytest

from pilot_space.application.services.note.content_converter import (
    BlockChangeType,
    ContentConverter,
)


@pytest.fixture
def converter() -> ContentConverter:
    return ContentConverter()


def _doc(*nodes: dict) -> dict:
    """Helper to wrap nodes in a TipTap doc."""
    return {"type": "doc", "content": list(nodes)}


def _p(text: str, *, block_id: str | None = None) -> dict:
    node: dict = {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _heading(text: str, level: int = 1, *, block_id: str | None = None) -> dict:
    node: dict = {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }
    if block_id:
        node["attrs"]["id"] = block_id
    return node


def _bold_text(text: str) -> dict:
    return {"type": "text", "marks": [{"type": "bold"}], "text": text}


def _italic_text(text: str) -> dict:
    return {"type": "text", "marks": [{"type": "italic"}], "text": text}


def _code_block(code: str, language: str = "", *, block_id: str | None = None) -> dict:
    attrs: dict = {"language": language}
    if block_id:
        attrs["id"] = block_id
    return {
        "type": "codeBlock",
        "attrs": attrs,
        "content": [{"type": "text", "text": code}],
    }


def _bullet_list(*items: str, block_id: str | None = None) -> dict:
    list_items = []
    for item in items:
        li: dict = {
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}],
        }
        list_items.append(li)
    node: dict = {"type": "bulletList", "content": list_items}
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _ordered_list(*items: str, block_id: str | None = None) -> dict:
    list_items = []
    for item in items:
        li: dict = {
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}],
        }
        list_items.append(li)
    node: dict = {"type": "orderedList", "content": list_items}
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _blockquote(text: str, *, block_id: str | None = None) -> dict:
    node: dict = {
        "type": "blockquote",
        "content": [_p(text)],
    }
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _hr() -> dict:
    return {"type": "horizontalRule"}


def _link_text(text: str, href: str) -> dict:
    return {"type": "text", "marks": [{"type": "link", "attrs": {"href": href}}], "text": text}


def _task_list(*items: tuple[str, bool], block_id: str | None = None) -> dict:
    list_items = []
    for text, checked in items:
        li: dict = {
            "type": "taskItem",
            "attrs": {"checked": checked},
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }
        list_items.append(li)
    node: dict = {"type": "taskList", "content": list_items}
    if block_id:
        node["attrs"] = {"id": block_id}
    return node


def _inline_issue(
    issue_id: str = "issue-uuid",
    issue_key: str = "PS-123",
    title: str = "Bug fix",
    issue_type: str = "bug",
    state: str = "todo",
    priority: str = "high",
) -> dict:
    return {
        "type": "inlineIssue",
        "attrs": {
            "issueId": issue_id,
            "issueKey": issue_key,
            "title": title,
            "type": issue_type,
            "state": state,
            "priority": priority,
        },
    }


# ============================================================
# tiptap_to_markdown tests
# ============================================================


class TestTipTapToMarkdown:
    def test_that_empty_doc_converts_to_empty_string(self, converter: ContentConverter) -> None:
        doc = _doc()
        result = converter.tiptap_to_markdown(doc)
        assert result == ""

    def test_that_paragraph_converts_to_markdown(self, converter: ContentConverter) -> None:
        doc = _doc(_p("Hello world"))
        result = converter.tiptap_to_markdown(doc)
        assert "Hello world" in result
        assert result.strip() == "Hello world"

    def test_that_heading_converts_with_level(self, converter: ContentConverter) -> None:
        doc = _doc(
            _heading("H1 Title", 1),
            _heading("H2 Title", 2),
            _heading("H3 Title", 3),
        )
        result = converter.tiptap_to_markdown(doc)
        assert "# H1 Title" in result
        assert "## H2 Title" in result
        assert "### H3 Title" in result

    def test_that_bold_mark_converts(self, converter: ContentConverter) -> None:
        doc = _doc(
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hello "},
                    _bold_text("world"),
                ],
            }
        )
        result = converter.tiptap_to_markdown(doc)
        assert "**world**" in result

    def test_that_italic_mark_converts(self, converter: ContentConverter) -> None:
        doc = _doc(
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hello "},
                    _italic_text("world"),
                ],
            }
        )
        result = converter.tiptap_to_markdown(doc)
        assert "*world*" in result

    def test_that_code_block_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_code_block("def foo(): pass", "python"))
        result = converter.tiptap_to_markdown(doc)
        assert "```python" in result
        assert "def foo(): pass" in result
        assert "```" in result

    def test_that_bullet_list_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_bullet_list("Item 1", "Item 2", "Item 3"))
        result = converter.tiptap_to_markdown(doc)
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_that_ordered_list_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_ordered_list("First", "Second", "Third"))
        result = converter.tiptap_to_markdown(doc)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result

    def test_that_block_ids_preserved_as_html_comments(self, converter: ContentConverter) -> None:
        bid = str(uuid.uuid4())
        doc = _doc(_p("Hello", block_id=bid))
        result = converter.tiptap_to_markdown(doc)
        assert f"<!-- block:{bid} -->" in result

    def test_that_inline_issue_node_converts(self, converter: ContentConverter) -> None:
        doc = _doc(
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "See "},
                    _inline_issue(issue_id="uuid-1", issue_key="PS-99", title="Fix login"),
                ],
            }
        )
        result = converter.tiptap_to_markdown(doc)
        assert "[PS-99]" in result
        assert "issue:uuid-1" in result

    def test_that_nested_content_converts_correctly(self, converter: ContentConverter) -> None:
        doc = _doc(
            _heading("Title", 1),
            _p("Introduction paragraph."),
            _bullet_list("Point A", "Point B"),
            _code_block("x = 1", "python"),
        )
        result = converter.tiptap_to_markdown(doc)
        assert "# Title" in result
        assert "Introduction paragraph." in result
        assert "- Point A" in result
        assert "```python" in result

    def test_that_blockquote_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_blockquote("A wise quote"))
        result = converter.tiptap_to_markdown(doc)
        assert "> " in result
        assert "A wise quote" in result

    def test_that_horizontal_rule_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_p("Before"), _hr(), _p("After"))
        result = converter.tiptap_to_markdown(doc)
        assert "---" in result

    def test_that_links_convert(self, converter: ContentConverter) -> None:
        doc = _doc(
            {
                "type": "paragraph",
                "content": [_link_text("Click here", "https://example.com")],
            }
        )
        result = converter.tiptap_to_markdown(doc)
        assert "[Click here](https://example.com)" in result

    def test_that_task_list_converts(self, converter: ContentConverter) -> None:
        doc = _doc(_task_list(("Done item", True), ("Pending item", False)))
        result = converter.tiptap_to_markdown(doc)
        assert "- [x] Done item" in result
        assert "- [ ] Pending item" in result


# ============================================================
# markdown_to_tiptap tests
# ============================================================


class TestMarkdownToTipTap:
    def test_that_empty_string_converts_to_empty_doc(self, converter: ContentConverter) -> None:
        result = converter.markdown_to_tiptap("")
        assert result["type"] == "doc"
        content = result.get("content", [])
        # Empty or single empty paragraph
        assert len(content) <= 1

    def test_that_paragraph_markdown_converts_to_tiptap(self, converter: ContentConverter) -> None:
        result = converter.markdown_to_tiptap("Hello world\n")
        assert result["type"] == "doc"
        content = result["content"]
        assert len(content) >= 1
        para = content[0]
        assert para["type"] == "paragraph"
        text_content = para.get("content", [])
        assert any(t.get("text", "").strip() == "Hello world" for t in text_content)

    def test_that_heading_markdown_converts_to_tiptap(self, converter: ContentConverter) -> None:
        result = converter.markdown_to_tiptap("## My Heading\n")
        content = result["content"]
        heading = content[0]
        assert heading["type"] == "heading"
        assert heading["attrs"]["level"] == 2

    def test_that_block_id_comments_restored(self, converter: ContentConverter) -> None:
        bid = str(uuid.uuid4())
        md = f"<!-- block:{bid} -->\nHello world\n"
        result = converter.markdown_to_tiptap(md)
        content = result["content"]
        # The paragraph following the comment should have the block ID
        found = False
        for node in content:
            attrs = node.get("attrs", {})
            if attrs.get("id") == bid:
                found = True
                break
        assert found, f"Block ID {bid} not found in converted content"

    def test_that_bold_italic_markdown_converts_to_marks(self, converter: ContentConverter) -> None:
        result = converter.markdown_to_tiptap("Hello **bold** and *italic*\n")
        content = result["content"]
        para = content[0]
        texts = para.get("content", [])
        marks_found = []
        for t in texts:
            for m in t.get("marks", []):
                marks_found.append(m["type"])
        assert "bold" in marks_found
        assert "italic" in marks_found

    def test_that_code_block_markdown_converts(self, converter: ContentConverter) -> None:
        md = "```python\ndef foo(): pass\n```\n"
        result = converter.markdown_to_tiptap(md)
        content = result["content"]
        code = content[0]
        assert code["type"] == "codeBlock"
        assert code["attrs"]["language"] == "python"

    def test_that_list_markdown_converts_to_tiptap(self, converter: ContentConverter) -> None:
        md = "- Item A\n- Item B\n"
        result = converter.markdown_to_tiptap(md)
        content = result["content"]
        assert content[0]["type"] == "bulletList"
        items = content[0]["content"]
        assert len(items) == 2

    def test_that_inline_issue_link_converts_to_node(self, converter: ContentConverter) -> None:
        md = 'See [PS-99](issue:uuid-1 "Fix login")\n'
        result = converter.markdown_to_tiptap(md)
        # Should find an inlineIssue node somewhere in the content
        found = False

        def _search(node: dict) -> None:
            nonlocal found
            if node.get("type") == "inlineIssue":
                assert node["attrs"]["issueKey"] == "PS-99"
                assert node["attrs"]["issueId"] == "uuid-1"
                found = True
            for child in node.get("content", []):
                _search(child)

        _search(result)
        assert found, "inlineIssue node not found in converted content"

    def test_that_task_list_markdown_converts(self, converter: ContentConverter) -> None:
        md = "- [x] Done\n- [ ] Not done\n"
        result = converter.markdown_to_tiptap(md)
        content = result["content"]
        task_list = content[0]
        assert task_list["type"] == "taskList"
        items = task_list["content"]
        assert items[0]["attrs"]["checked"] is True
        assert items[1]["attrs"]["checked"] is False


# ============================================================
# Round-trip tests
# ============================================================


class TestRoundTrip:
    def test_that_round_trip_preserves_content(self, converter: ContentConverter) -> None:
        original = _doc(
            _heading("Title", 1),
            _p("A paragraph with text."),
            _bullet_list("First", "Second"),
        )
        md = converter.tiptap_to_markdown(original)
        restored = converter.markdown_to_tiptap(md)

        # Extract text from both and compare
        def _extract_text(node: dict) -> str:
            parts: list[str] = []
            if node.get("type") == "text":
                parts.append(node.get("text", ""))
            for child in node.get("content", []):
                parts.append(_extract_text(child))
            return " ".join(p for p in parts if p)

        original_text = _extract_text(original)
        restored_text = _extract_text(restored)
        # All original text should be present in restored
        for word in ["Title", "paragraph", "text", "First", "Second"]:
            assert word in original_text
            assert word in restored_text

    def test_that_round_trip_preserves_block_ids(self, converter: ContentConverter) -> None:
        bid1 = str(uuid.uuid4())
        bid2 = str(uuid.uuid4())
        original = _doc(
            _p("First", block_id=bid1),
            _p("Second", block_id=bid2),
        )
        md = converter.tiptap_to_markdown(original)
        restored = converter.markdown_to_tiptap(md)

        found_ids: set[str] = set()

        def _collect_ids(node: dict) -> None:
            attrs = node.get("attrs", {})
            if attrs.get("id"):
                found_ids.add(attrs["id"])
            for child in node.get("content", []):
                _collect_ids(child)

        _collect_ids(restored)
        assert bid1 in found_ids, f"Block ID {bid1} lost in round-trip"
        assert bid2 in found_ids, f"Block ID {bid2} lost in round-trip"

    def test_that_complex_document_round_trips(self, converter: ContentConverter) -> None:
        bid = str(uuid.uuid4())
        original = _doc(
            _heading("Project Overview", 1, block_id=bid),
            _p("This is a description."),
            _code_block("print('hello')", "python"),
            _bullet_list("Task 1", "Task 2"),
            _blockquote("Important note"),
        )
        md = converter.tiptap_to_markdown(original)
        restored = converter.markdown_to_tiptap(md)

        # Verify structure types are preserved
        types = [n["type"] for n in restored.get("content", [])]
        assert "heading" in types
        assert "paragraph" in types
        assert "codeBlock" in types
        assert "bulletList" in types
        assert "blockquote" in types

        # Verify block ID preserved
        heading = next(n for n in restored["content"] if n["type"] == "heading")
        assert heading.get("attrs", {}).get("id") == bid


# ============================================================
# compute_block_diff tests
# ============================================================


class TestComputeBlockDiff:
    def test_that_identical_docs_produce_no_diff(self, converter: ContentConverter) -> None:
        bid = str(uuid.uuid4())
        doc = _doc(_p("Same text", block_id=bid))
        diff = converter.compute_block_diff(doc, doc)
        assert diff == []

    def test_that_modified_block_detected_as_replace(self, converter: ContentConverter) -> None:
        bid = str(uuid.uuid4())
        old = _doc(_p("Old text", block_id=bid))
        new = _doc(_p("New text", block_id=bid))
        diff = converter.compute_block_diff(old, new)
        assert len(diff) == 1
        assert diff[0].block_id == bid
        assert diff[0].change_type == BlockChangeType.REPLACE

    def test_that_new_block_detected_as_insert(self, converter: ContentConverter) -> None:
        bid1 = str(uuid.uuid4())
        bid2 = str(uuid.uuid4())
        old = _doc(_p("Existing", block_id=bid1))
        new = _doc(_p("Existing", block_id=bid1), _p("New block", block_id=bid2))
        diff = converter.compute_block_diff(old, new)
        inserts = [d for d in diff if d.change_type == BlockChangeType.INSERT]
        assert len(inserts) == 1
        assert inserts[0].block_id == bid2

    def test_that_removed_block_detected_as_delete(self, converter: ContentConverter) -> None:
        bid1 = str(uuid.uuid4())
        bid2 = str(uuid.uuid4())
        old = _doc(_p("Keep", block_id=bid1), _p("Remove", block_id=bid2))
        new = _doc(_p("Keep", block_id=bid1))
        diff = converter.compute_block_diff(old, new)
        deletes = [d for d in diff if d.change_type == BlockChangeType.DELETE]
        assert len(deletes) == 1
        assert deletes[0].block_id == bid2

    def test_that_multiple_changes_detected(self, converter: ContentConverter) -> None:
        bid1 = str(uuid.uuid4())
        bid2 = str(uuid.uuid4())
        bid3 = str(uuid.uuid4())
        old = _doc(
            _p("Original A", block_id=bid1),
            _p("Will be removed", block_id=bid2),
        )
        new = _doc(
            _p("Modified A", block_id=bid1),
            _p("Brand new", block_id=bid3),
        )
        diff = converter.compute_block_diff(old, new)
        types = {d.change_type for d in diff}
        assert BlockChangeType.REPLACE in types
        assert BlockChangeType.DELETE in types
        assert BlockChangeType.INSERT in types

    def test_that_blocks_without_ids_are_compared_by_position(
        self, converter: ContentConverter
    ) -> None:
        old = _doc(_p("First"), _p("Second"))
        new = _doc(_p("First"), _p("Changed"))
        diff = converter.compute_block_diff(old, new)
        # At minimum, should detect a positional change
        assert len(diff) >= 1
