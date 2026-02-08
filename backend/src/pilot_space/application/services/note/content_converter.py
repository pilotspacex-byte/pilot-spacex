"""Bidirectional TipTap JSONContent ↔ Markdown converter with block ID preservation.

Preserves block IDs as ``<!-- block:uuid -->`` comments (or ¶N refs with BlockRefMap).
Also computes structural diffs between two TipTap documents at the block level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pilot_space.ai.mcp.block_ref_map import BlockRefMap


class BlockChangeType(str, Enum):
    """Type of change detected between two document versions."""

    REPLACE = "replace"
    INSERT = "insert"
    DELETE = "delete"


@dataclass(frozen=True)
class BlockChange:
    """A single block-level change between two documents."""

    block_id: str
    change_type: BlockChangeType
    old_content: dict[str, Any] | None = None
    new_content: dict[str, Any] | None = None
    after_block_id: str | None = None


# Regex to parse block ID comments in markdown
_BLOCK_ID_RE = re.compile(r"<!-- block:([a-f0-9\-]+) -->")
# Regex to parse inline issue links: [PS-99](issue:uuid "title")
_ISSUE_LINK_RE = re.compile(r'\[([A-Z]+-\d+)\]\(issue:([^\s"]+)(?:\s+"([^"]*)")?\)')


class ContentConverter:
    """Bidirectional TipTap JSONContent ↔ Markdown converter."""

    # ------------------------------------------------------------------
    # TipTap → Markdown
    # ------------------------------------------------------------------

    def tiptap_to_markdown(
        self,
        content: dict[str, Any],
        *,
        block_ref_map: BlockRefMap | None = None,
    ) -> str:
        """Convert TipTap JSONContent to Markdown.

        With ``block_ref_map``, uses ``[¶N]`` prefix instead of ``<!-- block:uuid -->``.
        """
        if content.get("type") != "doc":
            return ""
        nodes: list[dict[str, Any]] = content.get("content", [])
        if not nodes:
            return ""
        parts: list[str] = []
        for node in nodes:
            parts.append(self._node_to_md(node, block_ref_map=block_ref_map))
        return "\n".join(parts)

    def _node_to_md(
        self,
        node: dict[str, Any],
        *,
        block_ref_map: BlockRefMap | None = None,
    ) -> str:
        """Convert a single TipTap node to Markdown."""
        node_type = node.get("type", "")
        block_id = self._get_block_id(node)

        if block_ref_map is not None and block_id and block_id in block_ref_map:
            ref = block_ref_map.to_ref(block_id)
            prefix = f"[{ref}] "
        elif block_id:
            prefix = f"<!-- block:{block_id} -->\n"
        else:
            prefix = ""

        handler = self._NODE_HANDLERS.get(node_type)
        if handler:
            return prefix + handler(self, node)
        # Fallback: try to extract text
        return prefix + self._inline_content_to_md(node.get("content", []))

    def _paragraph_to_md(self, node: dict[str, Any]) -> str:
        return self._inline_content_to_md(node.get("content", [])) + "\n"

    def _heading_to_md(self, node: dict[str, Any]) -> str:
        level = node.get("attrs", {}).get("level", 1)
        hashes = "#" * level
        text = self._inline_content_to_md(node.get("content", []))
        return f"{hashes} {text}\n"

    def _code_block_to_md(self, node: dict[str, Any]) -> str:
        lang = node.get("attrs", {}).get("language", "")
        code = ""
        for child in node.get("content", []):
            if child.get("type") == "text":
                code += child.get("text", "")
        return f"```{lang}\n{code}\n```\n"

    def _bullet_list_to_md(self, node: dict[str, Any]) -> str:
        lines: list[str] = []
        for item in node.get("content", []):
            text = self._list_item_text(item)
            lines.append(f"- {text}")
        return "\n".join(lines) + "\n"

    def _ordered_list_to_md(self, node: dict[str, Any]) -> str:
        lines: list[str] = []
        for i, item in enumerate(node.get("content", []), start=1):
            text = self._list_item_text(item)
            lines.append(f"{i}. {text}")
        return "\n".join(lines) + "\n"

    def _task_list_to_md(self, node: dict[str, Any]) -> str:
        lines: list[str] = []
        for item in node.get("content", []):
            checked = item.get("attrs", {}).get("checked", False)
            marker = "[x]" if checked else "[ ]"
            text = self._list_item_text(item)
            lines.append(f"- {marker} {text}")
        return "\n".join(lines) + "\n"

    def _blockquote_to_md(self, node: dict[str, Any]) -> str:
        inner_parts: list[str] = []
        for child in node.get("content", []):
            inner_parts.append(self._inline_content_to_md(child.get("content", [])))
        text = "\n".join(inner_parts)
        lines = text.split("\n")
        return "\n".join(f"> {line}" for line in lines) + "\n"

    def _horizontal_rule_to_md(self, _node: dict[str, Any]) -> str:
        return "---\n"

    def _list_item_text(self, item: dict[str, Any]) -> str:
        """Extract text from a listItem node."""
        parts: list[str] = []
        for child in item.get("content", []):
            parts.append(self._inline_content_to_md(child.get("content", [])))
        return " ".join(parts)

    def _inline_content_to_md(self, content: list[dict[str, Any]]) -> str:
        """Convert inline content (text nodes with marks) to Markdown."""
        parts: list[str] = []
        for node in content:
            if node.get("type") == "text":
                text = node.get("text", "")
                marks = node.get("marks", [])
                text = self._apply_marks(text, marks)
                parts.append(text)
            elif node.get("type") == "inlineIssue":
                parts.append(self._inline_issue_to_md(node))
            elif node.get("type") == "hardBreak":
                parts.append("  \n")
            else:
                # Recurse for unknown inline types
                inner = node.get("content", [])
                if inner:
                    parts.append(self._inline_content_to_md(inner))
        return "".join(parts)

    def _apply_marks(self, text: str, marks: list[dict[str, Any]]) -> str:
        """Wrap text with Markdown formatting based on TipTap marks."""
        for mark in marks:
            mark_type = mark.get("type", "")
            if mark_type == "bold":
                text = f"**{text}**"
            elif mark_type == "italic":
                text = f"*{text}*"
            elif mark_type == "code":
                text = f"`{text}`"
            elif mark_type == "strike":
                text = f"~~{text}~~"
            elif mark_type == "link":
                href = mark.get("attrs", {}).get("href", "")
                text = f"[{text}]({href})"
        return text

    def _inline_issue_to_md(self, node: dict[str, Any]) -> str:
        """Convert inlineIssue node to Markdown link format."""
        attrs = node.get("attrs", {})
        key = attrs.get("issueKey", "")
        issue_id = attrs.get("issueId", "")
        title = attrs.get("title", "")
        if title:
            return f'[{key}](issue:{issue_id} "{title}")'
        return f"[{key}](issue:{issue_id})"

    _NODE_HANDLERS: ClassVar[dict[str, Any]] = {
        "paragraph": _paragraph_to_md,
        "heading": _heading_to_md,
        "codeBlock": _code_block_to_md,
        "bulletList": _bullet_list_to_md,
        "orderedList": _ordered_list_to_md,
        "taskList": _task_list_to_md,
        "blockquote": _blockquote_to_md,
        "horizontalRule": _horizontal_rule_to_md,
    }

    @staticmethod
    def _get_block_id(node: dict[str, Any]) -> str | None:
        """Extract block ID from node attrs."""
        attrs = node.get("attrs")
        if not attrs:
            return None
        return attrs.get("id") or attrs.get("blockId") or None

    # ------------------------------------------------------------------
    # Markdown → TipTap
    # ------------------------------------------------------------------

    def markdown_to_tiptap(self, markdown: str) -> dict[str, Any]:
        """Convert Markdown string to TipTap JSONContent document.

        Block ID comments (``<!-- block:uuid -->``) are restored to node attrs.
        """
        if not markdown.strip():
            return {"type": "doc", "content": []}

        from markdown_it import MarkdownIt

        md = MarkdownIt("commonmark", {"html": True})
        md.enable("table")
        md.enable("strikethrough")
        tokens = md.parse(markdown)

        nodes = self._tokens_to_tiptap(tokens)
        nodes = self._assign_pending_block_ids(nodes, markdown)
        return {"type": "doc", "content": nodes}

    def _tokens_to_tiptap(self, tokens: list[Any]) -> list[dict[str, Any]]:
        """Convert markdown-it tokens to TipTap nodes."""
        nodes: list[dict[str, Any]] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            t_type = token.type

            if t_type == "heading_open":
                level = int(token.tag[1])  # h1 -> 1
                i += 1
                inline_token = tokens[i] if i < len(tokens) else None
                content = self._inline_to_tiptap(inline_token) if inline_token else []
                i += 1  # skip heading_close
                nodes.append(
                    {
                        "type": "heading",
                        "attrs": {"level": level},
                        "content": content,
                    }
                )
            elif t_type == "paragraph_open":
                i += 1
                inline_token = tokens[i] if i < len(tokens) else None
                content = self._inline_to_tiptap(inline_token) if inline_token else []
                i += 1  # skip paragraph_close
                nodes.append(
                    {
                        "type": "paragraph",
                        "content": content,
                    }
                )
            elif t_type == "fence":
                lang = token.info.strip() if token.info else ""
                code_text = token.content.rstrip("\n")
                nodes.append(
                    {
                        "type": "codeBlock",
                        "attrs": {"language": lang},
                        "content": [{"type": "text", "text": code_text}],
                    }
                )
            elif t_type == "bullet_list_open":
                items, i = self._parse_list_items(tokens, i + 1, "bullet_list_close")
                # Check for task list
                if self._is_task_list(items):
                    nodes.append({"type": "taskList", "content": items})
                else:
                    nodes.append({"type": "bulletList", "content": items})
            elif t_type == "ordered_list_open":
                items, i = self._parse_list_items(tokens, i + 1, "ordered_list_close")
                nodes.append({"type": "orderedList", "content": items})
            elif t_type == "blockquote_open":
                inner, i = self._parse_until_close(tokens, i + 1, "blockquote_close")
                nodes.append({"type": "blockquote", "content": inner})
            elif t_type == "hr":
                nodes.append({"type": "horizontalRule"})
            elif t_type == "html_block":
                # Check for block ID comment
                match = _BLOCK_ID_RE.search(token.content)
                if match:
                    # Will be assigned to next node in _assign_pending_block_ids
                    nodes.append({"type": "_block_id_marker", "_id": match.group(1)})
            i += 1
        return nodes

    def _parse_list_items(
        self, tokens: list[Any], start: int, close_type: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Parse list items from tokens."""
        items: list[dict[str, Any]] = []
        i = start
        while i < len(tokens):
            token = tokens[i]
            if token.type == close_type:
                return items, i
            if token.type == "list_item_open":
                item_content, i = self._parse_list_item_content(tokens, i + 1)
                item: dict[str, Any] = {"type": "listItem", "content": item_content}
                # Check for task item
                if item_content and self._is_task_item_content(item_content):
                    text_content, checked = self._extract_task_info(item_content)
                    item = {
                        "type": "taskItem",
                        "attrs": {"checked": checked},
                        "content": text_content,
                    }
                items.append(item)
            i += 1
        return items, i

    def _parse_list_item_content(
        self, tokens: list[Any], start: int
    ) -> tuple[list[dict[str, Any]], int]:
        """Parse content within a list item until list_item_close."""
        nodes: list[dict[str, Any]] = []
        i = start
        while i < len(tokens):
            token = tokens[i]
            if token.type == "list_item_close":
                return nodes, i
            if token.type == "paragraph_open":
                i += 1
                inline_token = tokens[i] if i < len(tokens) else None
                content = self._inline_to_tiptap(inline_token) if inline_token else []
                i += 1  # paragraph_close
                nodes.append({"type": "paragraph", "content": content})
            i += 1
        return nodes, i

    def _parse_until_close(
        self, tokens: list[Any], start: int, close_type: str
    ) -> tuple[list[dict[str, Any]], int]:
        """Parse tokens until a close token is found."""
        inner_tokens: list[Any] = []
        i = start
        depth = 1
        open_type = close_type.replace("_close", "_open")
        while i < len(tokens):
            token = tokens[i]
            if token.type == open_type:
                depth += 1
            elif token.type == close_type:
                depth -= 1
                if depth == 0:
                    break
            inner_tokens.append(token)
            i += 1
        return self._tokens_to_tiptap(inner_tokens), i

    def _inline_to_tiptap(self, token: Any) -> list[dict[str, Any]]:
        """Convert an inline token to TipTap text nodes."""
        if token is None or not hasattr(token, "children") or token.children is None:
            content = getattr(token, "content", "")
            if content:
                return [{"type": "text", "text": content}]
            return []

        nodes: list[dict[str, Any]] = []
        mark_stack: list[dict[str, Any]] = []

        for child in token.children:
            if child.type == "text":
                text = child.content
                # Check for inline issue links
                issue_match = _ISSUE_LINK_RE.search(text)
                if issue_match:
                    self._parse_text_with_issues(text, mark_stack, nodes)
                else:
                    node: dict[str, Any] = {"type": "text", "text": text}
                    if mark_stack:
                        node["marks"] = [m.copy() for m in mark_stack]
                    nodes.append(node)
            elif child.type == "code_inline":
                node = {"type": "text", "text": child.content, "marks": [{"type": "code"}]}
                nodes.append(node)
            elif child.type == "softbreak":
                nodes.append({"type": "hardBreak"})
            elif child.type == "strong_open":
                mark_stack.append({"type": "bold"})
            elif child.type == "strong_close":
                mark_stack[:] = [m for m in mark_stack if m["type"] != "bold"]
            elif child.type == "em_open":
                mark_stack.append({"type": "italic"})
            elif child.type == "em_close":
                mark_stack[:] = [m for m in mark_stack if m["type"] != "italic"]
            elif child.type == "s_open":
                mark_stack.append({"type": "strike"})
            elif child.type == "s_close":
                mark_stack[:] = [m for m in mark_stack if m["type"] != "strike"]
            elif child.type == "link_open":
                href = ""
                title = ""
                for attr_name, attr_val in (child.attrs or {}).items():
                    if attr_name == "href":
                        href = attr_val
                    elif attr_name == "title":
                        title = attr_val
                # Check if this is an issue link
                if href.startswith("issue:"):
                    issue_id = href[6:]
                    # Peek ahead for text + link_close
                    # The issue key text will follow as a text token
                    mark_stack.append(
                        {
                            "type": "_issue_link",
                            "issueId": issue_id,
                            "title": title,
                        }
                    )
                else:
                    link_mark: dict[str, Any] = {"type": "link", "attrs": {"href": href}}
                    if title:
                        link_mark["attrs"]["title"] = title
                    mark_stack.append(link_mark)
            elif child.type == "link_close":
                # Check if closing an issue link
                issue_idx = next(
                    (i for i, m in enumerate(mark_stack) if m.get("type") == "_issue_link"),
                    None,
                )
                if issue_idx is not None:
                    issue_mark = mark_stack.pop(issue_idx)
                    # The last text node should become an inlineIssue
                    if nodes and nodes[-1].get("type") == "text":
                        key_text = nodes.pop()["text"]
                        nodes.append(
                            {
                                "type": "inlineIssue",
                                "attrs": {
                                    "issueId": issue_mark["issueId"],
                                    "issueKey": key_text,
                                    "title": issue_mark.get("title", ""),
                                    "type": "task",
                                    "state": "backlog",
                                    "priority": "medium",
                                },
                            }
                        )
                else:
                    mark_stack[:] = [m for m in mark_stack if m.get("type") != "link"]

        return nodes

    def _parse_text_with_issues(
        self, text: str, marks: list[dict[str, Any]], nodes: list[dict[str, Any]]
    ) -> None:
        """Parse text that may contain inline issue references."""
        last_end = 0
        for match in _ISSUE_LINK_RE.finditer(text):
            # Text before the match
            before = text[last_end : match.start()]
            if before:
                node: dict[str, Any] = {"type": "text", "text": before}
                if marks:
                    node["marks"] = [m.copy() for m in marks]
                nodes.append(node)
            # Issue node
            nodes.append(
                {
                    "type": "inlineIssue",
                    "attrs": {
                        "issueId": match.group(2),
                        "issueKey": match.group(1),
                        "title": match.group(3) or "",
                        "type": "task",
                        "state": "backlog",
                        "priority": "medium",
                    },
                }
            )
            last_end = match.end()
        # Remaining text
        remaining = text[last_end:]
        if remaining:
            node = {"type": "text", "text": remaining}
            if marks:
                node["marks"] = [m.copy() for m in marks]
            nodes.append(node)

    @staticmethod
    def _is_task_list(items: list[dict[str, Any]]) -> bool:
        """Check if list items are task items."""
        return any(item.get("type") == "taskItem" for item in items)

    @staticmethod
    def _is_task_item_content(content: list[dict[str, Any]]) -> bool:
        """Check if list item content starts with a task checkbox."""
        if not content:
            return False
        para = content[0]
        if para.get("type") != "paragraph":
            return False
        texts = para.get("content", [])
        if not texts:
            return False
        first_text = texts[0].get("text", "")
        return first_text.startswith(("[ ] ", "[x] "))

    @staticmethod
    def _extract_task_info(
        content: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], bool]:
        """Extract task checkbox state and clean the text."""
        if not content:
            return content, False
        para = content[0].copy()
        texts = list(para.get("content", []))
        if texts:
            first = texts[0].copy()
            text = first.get("text", "")
            checked = text.startswith("[x] ")
            first["text"] = text[4:]  # Remove "[ ] " or "[x] "
            texts[0] = first
            para["content"] = texts
        else:
            checked = False
        return [para], checked

    def _assign_pending_block_ids(
        self, nodes: list[dict[str, Any]], _markdown: str
    ) -> list[dict[str, Any]]:
        """Assign block IDs from marker nodes to the following content nodes."""
        result: list[dict[str, Any]] = []
        pending_id: str | None = None

        for node in nodes:
            if node.get("type") == "_block_id_marker":
                pending_id = node.get("_id")
                continue
            if pending_id:
                attrs = node.get("attrs")
                if attrs is None:
                    node["attrs"] = {"id": pending_id}
                else:
                    attrs["id"] = pending_id
                pending_id = None
            result.append(node)

        return result

    # ------------------------------------------------------------------
    # Block diff computation
    # ------------------------------------------------------------------

    def compute_block_diff(
        self,
        old_content: dict[str, Any],
        new_content: dict[str, Any],
    ) -> list[BlockChange]:
        """Compare two TipTap documents and return block-level changes.

        Blocks are matched by their ``id`` attribute. Blocks without IDs
        are compared positionally within the unmatched remainder.

        Args:
            old_content: Previous TipTap document.
            new_content: New TipTap document.

        Returns:
            List of block changes (replace, insert, delete).
        """
        old_nodes = old_content.get("content", [])
        new_nodes = new_content.get("content", [])

        old_by_id = self._index_by_block_id(old_nodes)
        new_by_id = self._index_by_block_id(new_nodes)

        changes: list[BlockChange] = []

        old_ids = set(old_by_id.keys())
        new_ids = set(new_by_id.keys())

        # Deleted blocks: in old but not new
        for bid in old_ids - new_ids:
            changes.append(
                BlockChange(
                    block_id=bid,
                    change_type=BlockChangeType.DELETE,
                    old_content=old_by_id[bid],
                )
            )

        # Inserted blocks: in new but not old
        for bid in new_ids - old_ids:
            new_node = new_by_id[bid]
            # Find the preceding block ID for position reference
            after_id = self._find_preceding_id(new_nodes, bid)
            changes.append(
                BlockChange(
                    block_id=bid,
                    change_type=BlockChangeType.INSERT,
                    new_content=new_node,
                    after_block_id=after_id,
                )
            )

        # Modified blocks: in both, but content changed
        for bid in old_ids & new_ids:
            old_node = old_by_id[bid]
            new_node = new_by_id[bid]
            if self._node_content_differs(old_node, new_node):
                changes.append(
                    BlockChange(
                        block_id=bid,
                        change_type=BlockChangeType.REPLACE,
                        old_content=old_node,
                        new_content=new_node,
                    )
                )

        # Positional comparison for blocks without IDs
        old_unidentified = [n for n in old_nodes if not self._get_block_id(n)]
        new_unidentified = [n for n in new_nodes if not self._get_block_id(n)]

        for idx, (old_n, new_n) in enumerate(zip(old_unidentified, new_unidentified, strict=False)):
            if self._node_content_differs(old_n, new_n):
                pos_id = f"_pos_{idx}"
                changes.append(
                    BlockChange(
                        block_id=pos_id,
                        change_type=BlockChangeType.REPLACE,
                        old_content=old_n,
                        new_content=new_n,
                    )
                )

        return changes

    def _index_by_block_id(self, nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Build a dict mapping block IDs to their nodes."""
        index: dict[str, dict[str, Any]] = {}
        for node in nodes:
            bid = self._get_block_id(node)
            if bid:
                index[bid] = node
        return index

    def _find_preceding_id(self, nodes: list[dict[str, Any]], target_id: str) -> str | None:
        """Find the block ID of the node immediately before the target."""
        prev_id: str | None = None
        for node in nodes:
            bid = self._get_block_id(node)
            if bid == target_id:
                return prev_id
            if bid:
                prev_id = bid
        return prev_id

    @staticmethod
    def _node_content_differs(a: dict[str, Any], b: dict[str, Any]) -> bool:
        """Check if two nodes differ in content (ignoring attrs.id)."""
        # Compare type
        if a.get("type") != b.get("type"):
            return True
        # Compare content recursively (simple JSON equality excluding id attrs)
        a_content = a.get("content", [])
        b_content = b.get("content", [])

        def _normalize(node: dict[str, Any]) -> dict[str, Any]:
            result = dict(node)
            # Remove id from attrs for comparison
            if "attrs" in result:
                attrs = dict(result["attrs"])
                attrs.pop("id", None)
                attrs.pop("blockId", None)
                if attrs:
                    result["attrs"] = attrs
                else:
                    del result["attrs"]
            if "content" in result:
                result["content"] = [_normalize(c) for c in result["content"]]
            return result

        return _normalize({"content": a_content}) != _normalize({"content": b_content})
