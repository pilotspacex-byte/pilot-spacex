/**
 * jsonContentToMarkdown - Converts TipTap JSONContent to a markdown string.
 *
 * Used during TipTap -> Monaco migration: the notes API stores content as
 * JSONContent, but MonacoNoteEditor expects a plain markdown string.
 *
 * Handles: headings, paragraphs, bullet/ordered lists, code blocks,
 * blockquotes, horizontal rules, hard breaks, and inline marks
 * (bold, italic, code, link, strike).
 *
 * Unknown node types fall back to recursive text extraction.
 */

/** Minimal JSONContent shape matching TipTap's JSONContent type. */
interface JSONNode {
  type?: string;
  attrs?: Record<string, unknown>;
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>;
  text?: string;
  content?: JSONNode[];
}

/**
 * Convert TipTap JSONContent to a markdown string.
 *
 * @param content - TipTap JSONContent document (or undefined/null)
 * @returns Markdown string (empty string for undefined/null input)
 */
export function jsonContentToMarkdown(content: JSONNode | undefined | null): string {
  if (!content) return '';
  return renderNode(content).trim();
}

/** Render a single JSONContent node to markdown. */
function renderNode(node: JSONNode): string {
  switch (node.type) {
    case 'doc':
      return renderChildren(node);

    case 'heading': {
      const level = (node.attrs?.level as number) ?? 1;
      const prefix = '#'.repeat(Math.min(level, 6));
      return `${prefix} ${renderInline(node)}\n`;
    }

    case 'paragraph':
      return `${renderInline(node)}\n`;

    case 'bulletList':
      return renderList(node, 'bullet');

    case 'orderedList':
      return renderList(node, 'ordered');

    case 'listItem':
      return renderChildren(node);

    case 'codeBlock': {
      const lang = (node.attrs?.language as string) ?? '';
      const code = renderInline(node);
      return `\`\`\`${lang}\n${code}\n\`\`\`\n`;
    }

    case 'blockquote': {
      const inner = renderChildren(node);
      return (
        inner
          .split('\n')
          .map((line) => (line ? `> ${line}` : '>'))
          .join('\n') + '\n'
      );
    }

    case 'horizontalRule':
      return '---\n';

    case 'hardBreak':
      return '\n';

    case 'text':
      return renderText(node);

    default:
      // Unknown node: attempt to extract text content recursively
      if (node.content) {
        return renderChildren(node);
      }
      return node.text ?? '';
  }
}

/** Render children of a node, joining with newlines. */
function renderChildren(node: JSONNode): string {
  if (!node.content?.length) return '';
  return node.content.map(renderNode).join('\n');
}

/** Render inline content (text nodes within a block). */
function renderInline(node: JSONNode): string {
  if (!node.content?.length) return node.text ?? '';
  return node.content.map(renderNode).join('');
}

/** Render a list (bullet or ordered). */
function renderList(node: JSONNode, style: 'bullet' | 'ordered'): string {
  if (!node.content?.length) return '';
  return (
    node.content
      .map((item, index) => {
        const prefix = style === 'bullet' ? '- ' : `${index + 1}. `;
        const itemContent = renderInline(item).trim();
        return `${prefix}${itemContent}`;
      })
      .join('\n') + '\n'
  );
}

/** Render a text node, applying marks (bold, italic, code, link, strike). */
function renderText(node: JSONNode): string {
  let text = node.text ?? '';
  if (!node.marks?.length) return text;

  for (const mark of node.marks) {
    switch (mark.type) {
      case 'bold':
        text = `**${text}**`;
        break;
      case 'italic':
        text = `*${text}*`;
        break;
      case 'code':
        text = `\`${text}\``;
        break;
      case 'strike':
        text = `~~${text}~~`;
        break;
      case 'link': {
        const href = (mark.attrs?.href as string) ?? '';
        text = `[${text}](${href})`;
        break;
      }
    }
  }

  return text;
}
