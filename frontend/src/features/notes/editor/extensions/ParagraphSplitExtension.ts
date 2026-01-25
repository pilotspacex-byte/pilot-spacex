/**
 * ParagraphSplitExtension - Enhances paragraph splitting on double newlines
 *
 * This extension provides improved paragraph handling:
 * 1. Converts double Enter (two hard breaks) into a new paragraph during typing
 * 2. On paste, splits text with double newlines into separate paragraphs
 * 3. On render, normalizes consecutive hard breaks to proper paragraph structure
 *
 * Per UI Spec: Blocks are visually separated by double newlines for clear document structure.
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, type Transaction } from '@tiptap/pm/state';
import { type Node as ProseMirrorNode, Fragment, Slice, Schema } from '@tiptap/pm/model';

export interface ParagraphSplitOptions {
  /** Enable double hard break to paragraph conversion (default: true) */
  convertDoubleHardBreak: boolean;
  /** Enable paste transformation (default: true) */
  transformPaste: boolean;
  /** Enable content normalization on load (default: true) */
  normalizeOnLoad: boolean;
}

const PARAGRAPH_SPLIT_PLUGIN_KEY = new PluginKey('paragraphSplit');

/**
 * Checks if a node is a hard break
 */
function isHardBreak(node: ProseMirrorNode): boolean {
  return node.type.name === 'hardBreak';
}

/**
 * ParagraphSplitExtension - Ensures double newlines create proper paragraph separations
 *
 * Features:
 * - Typing: Two consecutive hard breaks (Enter + Enter) convert to new paragraph
 * - Paste: Text with \n\n splits into separate paragraphs
 * - Normalization: Cleans up consecutive hard breaks into proper structure
 */
export const ParagraphSplitExtension = Extension.create<ParagraphSplitOptions>({
  name: 'paragraphSplit',

  addOptions() {
    return {
      convertDoubleHardBreak: true,
      transformPaste: true,
      normalizeOnLoad: true,
    };
  },

  addProseMirrorPlugins() {
    const { convertDoubleHardBreak, transformPaste } = this.options;
    const editor = this.editor;

    return [
      new Plugin({
        key: PARAGRAPH_SPLIT_PLUGIN_KEY,

        // Handle paste transformation for double newlines
        props: {
          transformPasted: (slice: Slice) => {
            if (!transformPaste) return slice;

            const { schema } = editor.state;
            const content: ProseMirrorNode[] = [];

            // Process each node in the pasted content
            slice.content.forEach((node) => {
              if (node.type.name === 'paragraph') {
                // Split paragraph content by double newlines in text
                const splitNodes = splitParagraphByDoubleNewlines(node, schema);
                splitNodes.forEach((n) => content.push(n));
              } else {
                content.push(node);
              }
            });

            return new Slice(Fragment.from(content), slice.openStart, slice.openEnd);
          },
        },

        // Handle double hard break conversion during typing
        appendTransaction: (transactions, _oldState, newState) => {
          if (!convertDoubleHardBreak) return null;

          // Only process if there was an actual change
          const docChanged = transactions.some((tr) => tr.docChanged);
          if (!docChanged) return null;

          const tr: Transaction = newState.tr;
          let modified = false;

          // Find and convert consecutive hard breaks to paragraph splits
          newState.doc.descendants((node, pos, _parent) => {
            if (node.type.name !== 'paragraph') return true;

            // Check for consecutive hard breaks in this paragraph
            const hardBreakPositions = findConsecutiveHardBreaks(node);

            if (hardBreakPositions.length > 0) {
              // Split this paragraph at the hard breaks
              const splitResult = splitNodeAtHardBreaks(node, hardBreakPositions, newState.schema);

              if (splitResult) {
                // Replace the original paragraph with split paragraphs
                tr.replaceWith(pos, pos + node.nodeSize, splitResult);
                modified = true;
                return false; // Stop traversal after modification
              }
            }

            return true;
          });

          return modified ? tr : null;
        },
      }),
    ];
  },

  addKeyboardShortcuts() {
    return {
      // Double Enter creates a new paragraph with spacing
      Enter: ({ editor }) => {
        const { selection } = editor.state;
        const { $from } = selection;

        // Check if the previous character is a newline/hard break
        // If so, this Enter press should create a new paragraph
        const nodeBefore = $from.nodeBefore;

        if (nodeBefore && isHardBreak(nodeBefore)) {
          // We have a hard break before cursor - remove it and split to new paragraph
          return editor
            .chain()
            .deleteRange({
              from: $from.pos - 1,
              to: $from.pos,
            })
            .splitBlock()
            .run();
        }

        // Default behavior: let StarterKit handle it
        return false;
      },
    };
  },
});

/**
 * Find positions of consecutive hard breaks (two or more in a row)
 * Returns array of positions where splits should occur
 */
function findConsecutiveHardBreaks(node: ProseMirrorNode): number[] {
  const positions: number[] = [];
  let consecutiveCount = 0;
  let lastBreakPos = -1;

  node.content.forEach((child, offset) => {
    if (isHardBreak(child)) {
      consecutiveCount++;
      if (consecutiveCount >= 2) {
        positions.push(lastBreakPos); // Position of first break in sequence
        consecutiveCount = 0;
      }
      lastBreakPos = offset;
    } else {
      consecutiveCount = 0;
      lastBreakPos = -1;
    }
  });

  return positions;
}

/**
 * Split a paragraph node at hard break positions
 */
function splitNodeAtHardBreaks(
  node: ProseMirrorNode,
  breakPositions: number[],
  schema: Schema
): ProseMirrorNode[] | null {
  if (breakPositions.length === 0) return null;

  const paragraphs: ProseMirrorNode[] = [];
  const paragraphType = schema.nodes['paragraph'];

  if (!paragraphType) return null;

  let lastSplitPos = 0;
  const contentArr: ProseMirrorNode[] = [];
  node.content.forEach((child) => contentArr.push(child));

  // Process each break position
  for (const breakPos of breakPositions) {
    // Get content before this break (excluding the hard breaks themselves)
    const beforeContent: ProseMirrorNode[] = [];
    let i = lastSplitPos;

    while (i < contentArr.length) {
      const child = contentArr[i];
      if (!child) break;

      const currentOffset = getOffset(contentArr, i);

      if (currentOffset >= breakPos) {
        // Skip the consecutive hard breaks
        while (i < contentArr.length) {
          const c = contentArr[i];
          if (!c || !isHardBreak(c)) break;
          i++;
        }
        break;
      }

      if (!isHardBreak(child)) {
        beforeContent.push(child);
      }
      i++;
    }

    lastSplitPos = i;

    // Create paragraph from content before break
    if (beforeContent.length > 0) {
      paragraphs.push(paragraphType.create(node.attrs, Fragment.from(beforeContent)));
    } else {
      // Empty paragraph for visual spacing
      paragraphs.push(paragraphType.create(node.attrs));
    }
  }

  // Add remaining content after last break
  const remainingContent: ProseMirrorNode[] = [];
  for (let i = lastSplitPos; i < contentArr.length; i++) {
    const child = contentArr[i];
    if (child && !isHardBreak(child)) {
      remainingContent.push(child);
    }
  }

  if (remainingContent.length > 0 || paragraphs.length > 0) {
    paragraphs.push(
      paragraphType.create(
        node.attrs,
        remainingContent.length > 0 ? Fragment.from(remainingContent) : undefined
      )
    );
  }

  return paragraphs.length > 1 ? paragraphs : null;
}

/**
 * Calculate offset position within node content array
 */
function getOffset(contentArr: ProseMirrorNode[], index: number): number {
  let offset = 0;
  for (let i = 0; i < index; i++) {
    const node = contentArr[i];
    if (node) {
      offset += node.nodeSize;
    }
  }
  return offset;
}

/**
 * Split a paragraph by double newlines in its text content (for paste handling)
 */
function splitParagraphByDoubleNewlines(node: ProseMirrorNode, schema: Schema): ProseMirrorNode[] {
  // Extract text content
  const textContent = node.textContent;

  // Check for double newlines
  if (!textContent.includes('\n\n')) {
    return [node];
  }

  const paragraphType = schema.nodes['paragraph'];
  const textType = schema.nodes['text'];
  const hardBreakType = schema.nodes['hardBreak'];

  if (!paragraphType || !textType) {
    return [node];
  }

  const paragraphs: ProseMirrorNode[] = [];

  // Split by double newlines
  const parts = textContent.split(/\n\n+/);

  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed) {
      // Preserve single newlines as hard breaks
      const subParts = trimmed.split('\n');

      if (subParts.length === 1) {
        // Simple text
        paragraphs.push(paragraphType.create(node.attrs, schema.text(trimmed)));
      } else {
        // Has single newlines - convert to hard breaks
        const content: ProseMirrorNode[] = [];

        subParts.forEach((subPart, idx) => {
          if (subPart) {
            content.push(schema.text(subPart));
          }
          if (idx < subParts.length - 1 && hardBreakType) {
            content.push(hardBreakType.create());
          }
        });

        paragraphs.push(paragraphType.create(node.attrs, Fragment.from(content)));
      }
    } else {
      // Empty paragraph for visual spacing
      paragraphs.push(paragraphType.create(node.attrs));
    }
  }

  return paragraphs.length > 0 ? paragraphs : [node];
}

export default ParagraphSplitExtension;
