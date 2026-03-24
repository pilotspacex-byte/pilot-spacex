/**
 * rehypeMermaid - Rehype plugin to mark mermaid code blocks for React component replacement.
 *
 * Visits hast element nodes, finds <pre><code class="language-mermaid"> patterns,
 * and replaces the <pre> with a <div data-mermaid="{chart content}"> element.
 * The MarkdownPreview component maps these divs to the MermaidPreview React component.
 */
import { visit } from 'unist-util-visit';
import type { Root, Element, Text } from 'hast';

/**
 * Extract text content from a hast node tree (recursively collects Text nodes).
 */
function extractText(node: Element | Text): string {
  if (node.type === 'text') return node.value;
  if ('children' in node) {
    return (node.children as Array<Element | Text>).map(extractText).join('');
  }
  return '';
}

/**
 * Rehype plugin that converts mermaid code blocks into data-mermaid divs.
 */
export function rehypeMermaid() {
  return (tree: Root) => {
    visit(tree, 'element', (node: Element, index, parent) => {
      if (node.tagName !== 'pre' || !parent || index === undefined || index === null) {
        return;
      }

      // Find <code class="language-mermaid"> inside <pre>
      const codeChild = node.children.find((child): child is Element => {
        if (child.type !== 'element' || child.tagName !== 'code') return false;
        const classNames = child.properties?.className;
        return Array.isArray(classNames) && classNames.includes('language-mermaid');
      });

      if (!codeChild) return;

      // Extract the mermaid chart content from the code element
      const chartContent = extractText(codeChild).trim();

      // Replace the <pre> node with a <div data-mermaid="...">
      const replacement: Element = {
        type: 'element',
        tagName: 'div',
        properties: { 'data-mermaid': chartContent },
        children: [],
      };

      (parent as Element).children[index] = replacement;
    });
  };
}
