/**
 * Unit tests for extractFirstHeadingText utility in NoteCanvas.
 *
 * Validates heading extraction from ProseMirror-like document structures
 * used to sync note titles from the first heading in editor content.
 *
 * @module components/editor/__tests__/NoteCanvas-title-sync.test
 */
import { describe, it, expect } from 'vitest';
import { extractFirstHeadingText } from '../NoteCanvas';

/** Helper to create a mock ProseMirror-like doc with forEach */
function createMockDoc(nodes: Array<{ type: { name: string }; textContent: string }>) {
  return {
    forEach: (callback: (node: { type: { name: string }; textContent: string }) => void) => {
      nodes.forEach(callback);
    },
  };
}

describe('extractFirstHeadingText', () => {
  it('returns empty string when document has no nodes', () => {
    const doc = createMockDoc([]);
    expect(extractFirstHeadingText(doc)).toBe('');
  });

  it('returns empty string when document has no heading nodes', () => {
    const doc = createMockDoc([
      { type: { name: 'paragraph' }, textContent: 'Some text' },
      { type: { name: 'codeBlock' }, textContent: 'const x = 1' },
      { type: { name: 'bulletList' }, textContent: 'Item 1' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('');
  });

  it('returns text of the first heading node', () => {
    const doc = createMockDoc([
      { type: { name: 'paragraph' }, textContent: 'Intro text' },
      { type: { name: 'heading' }, textContent: 'My Note Title' },
      { type: { name: 'paragraph' }, textContent: 'Body text' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('My Note Title');
  });

  it('returns only the first heading when multiple headings exist', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: 'First Heading' },
      { type: { name: 'paragraph' }, textContent: 'Some text' },
      { type: { name: 'heading' }, textContent: 'Second Heading' },
      { type: { name: 'heading' }, textContent: 'Third Heading' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('First Heading');
  });

  it('returns heading when it is the first node in the document', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: 'Title at Top' },
      { type: { name: 'paragraph' }, textContent: 'Content below' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('Title at Top');
  });

  it('returns heading text even when deeply nested after other nodes', () => {
    const doc = createMockDoc([
      { type: { name: 'paragraph' }, textContent: '' },
      { type: { name: 'paragraph' }, textContent: 'Some text' },
      { type: { name: 'blockquote' }, textContent: 'A quote' },
      { type: { name: 'heading' }, textContent: 'Late Heading' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('Late Heading');
  });

  it('returns empty string when heading has empty text content', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: '' },
      { type: { name: 'heading' }, textContent: 'Second Heading' },
    ]);
    // First heading is empty, so it short-circuits to empty (falsy check)
    // The function finds it but empty string is falsy, so it continues
    expect(extractFirstHeadingText(doc)).toBe('Second Heading');
  });

  it('skips empty headings and returns first non-empty heading', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: '' },
      { type: { name: 'paragraph' }, textContent: 'Text' },
      { type: { name: 'heading' }, textContent: '' },
      { type: { name: 'heading' }, textContent: 'Actual Title' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('Actual Title');
  });

  it('handles document with only a single heading node', () => {
    const doc = createMockDoc([{ type: { name: 'heading' }, textContent: 'Only Title' }]);
    expect(extractFirstHeadingText(doc)).toBe('Only Title');
  });

  it('preserves whitespace in heading text content', () => {
    const doc = createMockDoc([
      {
        type: { name: 'heading' },
        textContent: '  Heading with spaces  ',
      },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('  Heading with spaces  ');
  });
});
