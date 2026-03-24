/**
 * markdownToJsonContent - Converts a markdown string to TipTap JSONContent.
 *
 * Inverse of jsonContentToMarkdown: the notes API stores content as
 * JSONContent, but MonacoNoteEditor emits plain markdown strings on change.
 *
 * Handles: headings, paragraphs, bullet/ordered lists, code blocks (including
 * pm:type markers), blockquotes, horizontal rules, and inline marks
 * (bold, italic, code).
 *
 * Unknown or empty lines become empty paragraphs (matching TipTap behavior).
 */

import type { JSONContent } from '@/types';

/** Safe line accessor — returns empty string for out-of-bounds indices. */
function lineAt(lines: string[], index: number): string {
  return lines[index] ?? '';
}

/**
 * Convert a markdown string to TipTap JSONContent document.
 *
 * @param markdown - Markdown string (empty/null returns minimal doc)
 * @returns TipTap JSONContent with type: 'doc'
 */
export function markdownToJsonContent(markdown: string | undefined | null): JSONContent {
  if (!markdown) {
    return { type: 'doc', content: [{ type: 'paragraph' }] };
  }

  const lines = markdown.split('\n');
  const content: JSONContent[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lineAt(lines, i);

    // Code block (``` with optional language, including pm:type blocks)
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lineAt(lines, i).startsWith('```')) {
        codeLines.push(lineAt(lines, i));
        i++;
      }
      // Skip closing ```
      if (i < lines.length) i++;

      const codeText = codeLines.join('\n');
      const node: JSONContent = {
        type: 'codeBlock',
        attrs: { language: lang || null },
      };
      if (codeText) {
        node.content = [{ type: 'text', text: codeText }];
      }
      content.push(node);
      continue;
    }

    // Horizontal rule
    if (/^---+\s*$/.test(line) || /^\*\*\*+\s*$/.test(line) || /^___+\s*$/.test(line)) {
      content.push({ type: 'horizontalRule' });
      i++;
      continue;
    }

    // Heading (# to ######)
    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = (headingMatch[1] ?? '').length;
      const text = headingMatch[2] ?? '';
      content.push({
        type: 'heading',
        attrs: { level },
        content: parseInline(text),
      });
      i++;
      continue;
    }

    // Blockquote (> text) — collect consecutive blockquote lines
    if (line.startsWith('> ') || line === '>') {
      const quoteLines: string[] = [];
      while (i < lines.length && (lineAt(lines, i).startsWith('> ') || lineAt(lines, i) === '>')) {
        const cur = lineAt(lines, i);
        const qLine = cur === '>' ? '' : cur.slice(2);
        quoteLines.push(qLine);
        i++;
      }
      // Parse inner content as paragraphs
      const innerContent: JSONContent[] = [];
      for (const ql of quoteLines) {
        if (ql === '') {
          innerContent.push({ type: 'paragraph' });
        } else {
          innerContent.push({
            type: 'paragraph',
            content: parseInline(ql),
          });
        }
      }
      content.push({
        type: 'blockquote',
        content: innerContent.length > 0 ? innerContent : [{ type: 'paragraph' }],
      });
      continue;
    }

    // Unordered list (- item or * item)
    if (/^[-*]\s+/.test(line)) {
      const items: JSONContent[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lineAt(lines, i))) {
        const itemText = lineAt(lines, i).replace(/^[-*]\s+/, '');
        items.push({
          type: 'listItem',
          content: [
            {
              type: 'paragraph',
              content: parseInline(itemText),
            },
          ],
        });
        i++;
      }
      content.push({ type: 'bulletList', content: items });
      continue;
    }

    // Ordered list (1. item, 2. item, etc.)
    if (/^\d+\.\s+/.test(line)) {
      const items: JSONContent[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lineAt(lines, i))) {
        const itemText = lineAt(lines, i).replace(/^\d+\.\s+/, '');
        items.push({
          type: 'listItem',
          content: [
            {
              type: 'paragraph',
              content: parseInline(itemText),
            },
          ],
        });
        i++;
      }
      content.push({ type: 'orderedList', content: items });
      continue;
    }

    // Empty line -> empty paragraph
    if (line.trim() === '') {
      content.push({ type: 'paragraph' });
      i++;
      continue;
    }

    // Default: paragraph
    content.push({
      type: 'paragraph',
      content: parseInline(line),
    });
    i++;
  }

  return {
    type: 'doc',
    content: content.length > 0 ? content : [{ type: 'paragraph' }],
  };
}

/**
 * Parse inline markdown (bold, italic, code) into TipTap text nodes with marks.
 *
 * Handles: **bold**, *italic*, `code`, and combinations thereof.
 * Returns an array of text nodes suitable for TipTap JSONContent.
 */
function parseInline(text: string): JSONContent[] {
  if (!text) return [{ type: 'text', text: ' ' }];

  const nodes: JSONContent[] = [];
  // Regex matches: **bold**, *italic*, `code`
  // Order matters: **bold** must come before *italic*
  const pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      const before = text.slice(lastIndex, match.index);
      if (before) {
        nodes.push({ type: 'text', text: before });
      }
    }

    if (match[2] !== undefined) {
      // **bold**
      nodes.push({
        type: 'text',
        text: match[2],
        marks: [{ type: 'bold' }],
      });
    } else if (match[3] !== undefined) {
      // *italic*
      nodes.push({
        type: 'text',
        text: match[3],
        marks: [{ type: 'italic' }],
      });
    } else if (match[4] !== undefined) {
      // `code`
      nodes.push({
        type: 'text',
        text: match[4],
        marks: [{ type: 'code' }],
      });
    }

    lastIndex = match.index + match[0].length;
  }

  // Remaining text after last match
  if (lastIndex < text.length) {
    nodes.push({ type: 'text', text: text.slice(lastIndex) });
  }

  return nodes.length > 0 ? nodes : [{ type: 'text', text }];
}
