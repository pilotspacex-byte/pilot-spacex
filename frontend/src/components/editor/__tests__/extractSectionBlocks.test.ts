import { describe, it, expect } from 'vitest';
import { extractSectionBlocks } from '../AutoTOC';
import type { Editor } from '@tiptap/react';

/**
 * Create a mock editor with a flat document structure.
 * Each block has a type, blockId, optional level (for headings), and textContent.
 * Simulates ProseMirror doc with nodeSize, content.size, and nodesBetween.
 */
function createMockEditor(
  blocks: Array<{ type: string; blockId: string; level?: number; textContent: string }>
): Editor {
  const NODE_SIZE = 10; // fixed per node for simplicity

  const children = blocks.map((block) => ({
    type: { name: block.type },
    attrs: { blockId: block.blockId, level: block.level ?? undefined },
    textContent: block.textContent,
    nodeSize: NODE_SIZE,
    isBlock: true,
    isTextblock: block.type === 'paragraph' || block.type === 'heading',
  }));

  return {
    state: {
      doc: {
        childCount: children.length,
        child: (i: number) => children[i],
        content: { size: children.length * NODE_SIZE },
        nodesBetween: (
          from: number,
          to: number,
          callback: (node: (typeof children)[0]) => boolean
        ) => {
          for (const child of children) {
            // compute this child's offset
            const idx = children.indexOf(child);
            const offset = idx * NODE_SIZE;
            if (offset >= from && offset < to) {
              const cont = callback(child);
              if (cont === false) break;
            }
          }
        },
      },
    },
  } as unknown as Editor;
}

describe('extractSectionBlocks', () => {
  it('should extract blocks from heading to next same-level heading', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1-intro', level: 1, textContent: 'Introduction' },
      { type: 'paragraph', blockId: 'p1', textContent: 'Some intro text' },
      { type: 'paragraph', blockId: 'p2', textContent: 'More intro text' },
      { type: 'heading', blockId: 'h1-main', level: 1, textContent: 'Main Content' },
      { type: 'paragraph', blockId: 'p3', textContent: 'Main content text' },
    ]);

    const result = extractSectionBlocks(editor, 'h1-intro');

    expect(result.blockIds).toEqual(['h1-intro', 'p1', 'p2']);
    expect(result.text).toBe('Introduction\nSome intro text\nMore intro text');
  });

  it('should include sub-headings within the section', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1-a', level: 1, textContent: 'Section A' },
      { type: 'heading', blockId: 'h2-a1', level: 2, textContent: 'Subsection A.1' },
      { type: 'paragraph', blockId: 'p1', textContent: 'Content' },
      { type: 'heading', blockId: 'h2-a2', level: 2, textContent: 'Subsection A.2' },
      { type: 'paragraph', blockId: 'p2', textContent: 'More content' },
      { type: 'heading', blockId: 'h1-b', level: 1, textContent: 'Section B' },
    ]);

    const result = extractSectionBlocks(editor, 'h1-a');

    expect(result.blockIds).toEqual(['h1-a', 'h2-a1', 'p1', 'h2-a2', 'p2']);
    expect(result.text).toContain('Section A');
    expect(result.text).toContain('Subsection A.1');
    expect(result.text).toContain('Subsection A.2');
  });

  it('should extract H2 section stopping at next H2 or H1', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1-parent', level: 1, textContent: 'Parent' },
      { type: 'heading', blockId: 'h2-first', level: 2, textContent: 'First Sub' },
      { type: 'paragraph', blockId: 'p1', textContent: 'First content' },
      { type: 'heading', blockId: 'h3-nested', level: 3, textContent: 'Nested' },
      { type: 'paragraph', blockId: 'p2', textContent: 'Nested content' },
      { type: 'heading', blockId: 'h2-second', level: 2, textContent: 'Second Sub' },
      { type: 'paragraph', blockId: 'p3', textContent: 'Second content' },
    ]);

    const result = extractSectionBlocks(editor, 'h2-first');

    expect(result.blockIds).toEqual(['h2-first', 'p1', 'h3-nested', 'p2']);
    expect(result.text).not.toContain('Second Sub');
  });

  it('should extract last section to end of document', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1-a', level: 1, textContent: 'First' },
      { type: 'paragraph', blockId: 'p1', textContent: 'First text' },
      { type: 'heading', blockId: 'h1-b', level: 1, textContent: 'Last' },
      { type: 'paragraph', blockId: 'p2', textContent: 'Last text' },
      { type: 'paragraph', blockId: 'p3', textContent: 'Final paragraph' },
    ]);

    const result = extractSectionBlocks(editor, 'h1-b');

    expect(result.blockIds).toEqual(['h1-b', 'p2', 'p3']);
    expect(result.text).toBe('Last\nLast text\nFinal paragraph');
  });

  it('should return empty when heading not found', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1', level: 1, textContent: 'Title' },
      { type: 'paragraph', blockId: 'p1', textContent: 'Content' },
    ]);

    const result = extractSectionBlocks(editor, 'nonexistent');

    expect(result.blockIds).toEqual([]);
    expect(result.text).toBe('');
  });

  it('should skip blocks without blockId', () => {
    const editor = createMockEditor([
      { type: 'heading', blockId: 'h1', level: 1, textContent: 'Title' },
      { type: 'paragraph', blockId: '', textContent: 'No ID block' },
      { type: 'paragraph', blockId: 'p1', textContent: 'Has ID' },
    ]);

    const result = extractSectionBlocks(editor, 'h1');

    // Empty string blockId is falsy, so it should be skipped
    expect(result.blockIds).toEqual(['h1', 'p1']);
  });
});
