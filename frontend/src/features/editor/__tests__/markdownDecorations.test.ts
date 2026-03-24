import { describe, it, expect } from 'vitest';
import {
  parseMarkdownLine,
  HEADING_REGEX,
  BOLD_REGEX,
  ITALIC_REGEX,
  INLINE_CODE_REGEX,
  LIST_REGEX,
  BLOCKQUOTE_REGEX,
} from '../decorations/markdownDecorations';

describe('markdownDecorations', () => {
  describe('HEADING_REGEX', () => {
    it('matches H1', () => {
      expect(HEADING_REGEX.test('# Title')).toBe(true);
    });

    it('matches H2', () => {
      expect(HEADING_REGEX.test('## Subtitle')).toBe(true);
    });

    it('matches H3', () => {
      expect(HEADING_REGEX.test('### Third Level')).toBe(true);
    });

    it('does not match non-heading lines', () => {
      expect(HEADING_REGEX.test('not a heading')).toBe(false);
      expect(HEADING_REGEX.test('#no space')).toBe(false);
    });
  });

  describe('BOLD_REGEX', () => {
    it('matches **bold text**', () => {
      expect(BOLD_REGEX.test('some **bold text** here')).toBe(true);
    });

    it('captures the bold range', () => {
      const match = BOLD_REGEX.exec('some **bold text** here');
      expect(match).not.toBeNull();
      expect(match![1]).toBe('bold text');
    });
  });

  describe('ITALIC_REGEX', () => {
    it('matches *italic* with asterisks', () => {
      expect(ITALIC_REGEX.test('some *italic* here')).toBe(true);
    });

    it('matches _italic_ with underscores', () => {
      expect(ITALIC_REGEX.test('some _italic_ here')).toBe(true);
    });

    it('does not match underscores within words', () => {
      // snake_case_name should NOT match italic
      expect(ITALIC_REGEX.test('not_italic_text')).toBe(false);
    });
  });

  describe('INLINE_CODE_REGEX', () => {
    it('matches `code`', () => {
      expect(INLINE_CODE_REGEX.test('some `code` here')).toBe(true);
    });

    it('captures the code content', () => {
      const match = INLINE_CODE_REGEX.exec('some `inline code` here');
      expect(match).not.toBeNull();
      expect(match![1]).toBe('inline code');
    });
  });

  describe('LIST_REGEX', () => {
    it('matches "- item"', () => {
      expect(LIST_REGEX.test('- item')).toBe(true);
    });

    it('matches "* item"', () => {
      expect(LIST_REGEX.test('* item')).toBe(true);
    });

    it('matches "1. item"', () => {
      expect(LIST_REGEX.test('1. item')).toBe(true);
    });

    it('matches indented list items', () => {
      expect(LIST_REGEX.test('  - nested item')).toBe(true);
    });
  });

  describe('BLOCKQUOTE_REGEX', () => {
    it('matches "> quote"', () => {
      expect(BLOCKQUOTE_REGEX.test('> quote text')).toBe(true);
    });

    it('does not match > in middle of text', () => {
      expect(BLOCKQUOTE_REGEX.test('a > b')).toBe(false);
    });
  });

  describe('parseMarkdownLine', () => {
    it('returns heading decoration for H1', () => {
      const decorations = parseMarkdownLine('# Hello World');
      expect(decorations).toContainEqual(expect.objectContaining({ type: 'heading', level: 1 }));
    });

    it('returns heading decoration for H2', () => {
      const decorations = parseMarkdownLine('## Hello World');
      expect(decorations).toContainEqual(expect.objectContaining({ type: 'heading', level: 2 }));
    });

    it('returns heading decoration for H3', () => {
      const decorations = parseMarkdownLine('### Hello World');
      expect(decorations).toContainEqual(expect.objectContaining({ type: 'heading', level: 3 }));
    });

    it('returns bold decoration for **text**', () => {
      const decorations = parseMarkdownLine('some **bold** text');
      expect(decorations).toContainEqual(
        expect.objectContaining({ type: 'bold', startCol: 6, endCol: 14 })
      );
    });

    it('returns italic decoration for *text*', () => {
      const decorations = parseMarkdownLine('some *italic* text');
      expect(decorations).toContainEqual(
        expect.objectContaining({ type: 'italic', startCol: 6, endCol: 14 })
      );
    });

    it('returns code decoration for `code`', () => {
      const decorations = parseMarkdownLine('some `code` text');
      expect(decorations).toContainEqual(
        expect.objectContaining({ type: 'code', startCol: 6, endCol: 12 })
      );
    });

    it('returns list decoration for - item', () => {
      const decorations = parseMarkdownLine('- list item');
      expect(decorations).toContainEqual(expect.objectContaining({ type: 'list' }));
    });

    it('returns blockquote decoration for > quote', () => {
      const decorations = parseMarkdownLine('> blockquote');
      expect(decorations).toContainEqual(expect.objectContaining({ type: 'blockquote' }));
    });

    it('returns both heading and bold for mixed line', () => {
      const decorations = parseMarkdownLine('# **Bold heading**');
      const types = decorations.map((d) => d.type);
      expect(types).toContain('heading');
      expect(types).toContain('bold');
    });

    it('returns empty array for plain text', () => {
      const decorations = parseMarkdownLine('plain text with no formatting');
      expect(decorations).toEqual([]);
    });

    it('does not match underscores within words as italic', () => {
      const decorations = parseMarkdownLine('not_italic_text');
      const italics = decorations.filter((d) => d.type === 'italic');
      expect(italics).toHaveLength(0);
    });
  });
});
