import { describe, it, expect } from 'vitest';
import { parseMarkdownSymbols } from './markdownSymbols';

describe('parseMarkdownSymbols', () => {
  it('extracts H1 heading as level=1', () => {
    const symbols = parseMarkdownSymbols('# Title');
    expect(symbols).toHaveLength(1);
    expect(symbols[0]!.name).toBe('Title');
    expect(symbols[0]!.kind).toBe('heading');
    expect(symbols[0]!.level).toBe(1);
    expect(symbols[0]!.line).toBe(1);
  });

  it('extracts H2 nested under preceding H1', () => {
    const content = '# Title\n\n## Subtitle';
    const symbols = parseMarkdownSymbols(content);
    expect(symbols).toHaveLength(1);
    expect(symbols[0]!.children).toHaveLength(1);
    expect(symbols[0]!.children[0]!.name).toBe('Subtitle');
    expect(symbols[0]!.children[0]!.level).toBe(2);
  });

  it('extracts H3 nested under preceding H2', () => {
    const content = '# Title\n## Section\n### Deep';
    const symbols = parseMarkdownSymbols(content);
    expect(symbols).toHaveLength(1);
    const h2 = symbols[0]!.children[0]!;
    expect(h2.children).toHaveLength(1);
    expect(h2.children[0]!.name).toBe('Deep');
    expect(h2.children[0]!.level).toBe(3);
  });

  it('multiple H1s create flat siblings at top level', () => {
    const content = '# First\n# Second';
    const symbols = parseMarkdownSymbols(content);
    expect(symbols).toHaveLength(2);
    expect(symbols[0]!.name).toBe('First');
    expect(symbols[1]!.name).toBe('Second');
  });

  it('extracts PM block as kind=pm-block nested under preceding heading', () => {
    const content = '# Overview\n\n```pm:decision\n{"title":"go"}\n```';
    const symbols = parseMarkdownSymbols(content);
    expect(symbols).toHaveLength(1);
    expect(symbols[0]!.children).toHaveLength(1);
    expect(symbols[0]!.children[0]!.kind).toBe('pm-block');
    expect(symbols[0]!.children[0]!.name).toBe('decision');
  });

  it('returns empty array for empty content', () => {
    expect(parseMarkdownSymbols('')).toEqual([]);
  });

  it('produces correct hierarchy for mixed headings and PM blocks', () => {
    const content = [
      '# Project',
      '## Design',
      '```pm:risk\n{}\n```',
      '## Implementation',
      '### Backend',
    ].join('\n');
    const symbols = parseMarkdownSymbols(content);

    expect(symbols).toHaveLength(1);
    const project = symbols[0]!;
    expect(project.children).toHaveLength(2); // Design, Implementation

    const design = project.children[0]!;
    expect(design.name).toBe('Design');
    expect(design.children).toHaveLength(1); // risk PM block
    expect(design.children[0]!.kind).toBe('pm-block');

    const impl = project.children[1]!;
    expect(impl.name).toBe('Implementation');
    expect(impl.children).toHaveLength(1); // Backend
    expect(impl.children[0]!.name).toBe('Backend');
  });

  it('H2 followed by H1 creates new top-level node (not nested)', () => {
    const content = '## Orphan\n# Main';
    const symbols = parseMarkdownSymbols(content);
    expect(symbols).toHaveLength(2);
    expect(symbols[0]!.name).toBe('Orphan');
    expect(symbols[0]!.level).toBe(2);
    expect(symbols[1]!.name).toBe('Main');
    expect(symbols[1]!.level).toBe(1);
  });
});
