import { describe, it, expect } from 'vitest';
import { extractHeadings } from '../lib/markdown-headings';

describe('extractHeadings', () => {
  it('should extract h1-h4 headings', () => {
    const md = `# Title\n## Section\n### Subsection\n#### Detail`;
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(4);
    expect(headings[0]).toEqual({ id: 'title', text: 'Title', level: 1 });
    expect(headings[1]).toEqual({ id: 'section', text: 'Section', level: 2 });
    expect(headings[2]).toEqual({ id: 'subsection', text: 'Subsection', level: 3 });
    expect(headings[3]).toEqual({ id: 'detail', text: 'Detail', level: 4 });
  });

  it('should generate URL-safe slug IDs', () => {
    const md = `## Hello World & Friends!`;
    const headings = extractHeadings(md);
    expect(headings[0]?.id).toBe('hello-world-friends');
  });

  it('should strip markdown formatting from heading text', () => {
    const md = `## **Bold** and _italic_ heading`;
    const headings = extractHeadings(md);
    expect(headings[0]?.text).toBe('Bold and italic heading');
  });

  it('should skip headings inside multi-line code blocks', () => {
    const md = '```\n## Not a heading\nsome code\n```\n## Real heading';
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0]?.text).toBe('Real heading');
  });

  it('should skip headings inside tilde code fences', () => {
    const md = '~~~\n## Not a heading\nsome code\n~~~\n## Real heading';
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0]?.text).toBe('Real heading');
  });

  it('should handle mixed fence markers correctly (backtick open, tilde inside)', () => {
    const md = '```\n~~~\n## Not a heading\n~~~\n```\n## Real heading';
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0]?.text).toBe('Real heading');
  });

  it('should deduplicate heading IDs with suffix', () => {
    const md = '## Setup\n## Setup\n## Setup';
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(3);
    expect(headings[0]?.id).toBe('setup');
    expect(headings[1]?.id).toBe('setup-1');
    expect(headings[2]?.id).toBe('setup-2');
  });

  it('should return empty array for no headings', () => {
    const md = 'Just some text without headings.';
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(0);
  });
});
