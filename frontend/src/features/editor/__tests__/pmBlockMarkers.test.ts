import { describe, it, expect } from 'vitest';
import {
  parsePMBlockMarkers,
  PM_BLOCK_REGEX,
  PM_BLOCK_CLOSE_REGEX,
  PM_BLOCK_TYPES,
} from '../markers/pmBlockMarkers';
import type { PMBlockMarker } from '../types';

describe('PM_BLOCK_REGEX', () => {
  it('matches opening pm block markers', () => {
    expect(PM_BLOCK_REGEX.test('```pm:decision')).toBe(true);
    expect(PM_BLOCK_REGEX.test('```pm:sprint-board')).toBe(true);
  });

  it('does not match regular code blocks', () => {
    expect(PM_BLOCK_REGEX.test('```typescript')).toBe(false);
    expect(PM_BLOCK_REGEX.test('```')).toBe(false);
  });
});

describe('PM_BLOCK_CLOSE_REGEX', () => {
  it('matches closing triple backticks', () => {
    expect(PM_BLOCK_CLOSE_REGEX.test('```')).toBe(true);
  });

  it('does not match opening markers', () => {
    expect(PM_BLOCK_CLOSE_REGEX.test('```pm:decision')).toBe(false);
  });
});

describe('PM_BLOCK_TYPES', () => {
  it('contains all 10 PM block types', () => {
    expect(PM_BLOCK_TYPES).toHaveLength(10);
    expect(PM_BLOCK_TYPES).toContain('decision');
    expect(PM_BLOCK_TYPES).toContain('raci');
    expect(PM_BLOCK_TYPES).toContain('risk');
    expect(PM_BLOCK_TYPES).toContain('dependency');
    expect(PM_BLOCK_TYPES).toContain('timeline');
    expect(PM_BLOCK_TYPES).toContain('sprint-board');
    expect(PM_BLOCK_TYPES).toContain('dashboard');
    expect(PM_BLOCK_TYPES).toContain('form');
    expect(PM_BLOCK_TYPES).toContain('release-notes');
    expect(PM_BLOCK_TYPES).toContain('capacity-plan');
  });
});

describe('parsePMBlockMarkers', () => {
  it('parses a single pm:decision block with valid JSON', () => {
    const text = '# Hello\n\n```pm:decision\n{"id":"d1","title":"Use Monaco"}\n```\n\nMore text';
    const result = parsePMBlockMarkers(text);

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual<PMBlockMarker>({
      type: 'decision',
      startLine: 3,
      endLine: 5,
      data: { id: 'd1', title: 'Use Monaco' },
      raw: '{"id":"d1","title":"Use Monaco"}',
    });
  });

  it('returns empty array when no pm blocks present', () => {
    expect(parsePMBlockMarkers('no blocks here')).toEqual([]);
  });

  it('parses multiple pm blocks in order', () => {
    const text = [
      '```pm:decision',
      '{"id":"d1"}',
      '```',
      '',
      '```pm:risk',
      '{"id":"r1"}',
      '```',
    ].join('\n');

    const result = parsePMBlockMarkers(text);
    expect(result).toHaveLength(2);
    expect(result[0]!.type).toBe('decision');
    expect(result[0]!.startLine).toBe(1);
    expect(result[0]!.endLine).toBe(3);
    expect(result[1]!.type).toBe('risk');
    expect(result[1]!.startLine).toBe(5);
    expect(result[1]!.endLine).toBe(7);
  });

  it('ignores non-pm code blocks', () => {
    const text = [
      '```typescript',
      'const x = 1;',
      '```',
      '',
      '```pm:decision',
      '{"id":"d1"}',
      '```',
    ].join('\n');

    const result = parsePMBlockMarkers(text);
    expect(result).toHaveLength(1);
    expect(result[0]!.type).toBe('decision');
  });

  it('returns data as null for malformed JSON', () => {
    const text = '```pm:decision\nnot valid json\n```';
    const result = parsePMBlockMarkers(text);

    expect(result).toHaveLength(1);
    expect(result[0]!.data).toBeNull();
    expect(result[0]!.raw).toBe('not valid json');
  });

  it('detects all 10 PM block types', () => {
    const types = [
      'decision',
      'raci',
      'risk',
      'dependency',
      'timeline',
      'sprint-board',
      'dashboard',
      'form',
      'release-notes',
      'capacity-plan',
    ];

    for (const type of types) {
      const text = `\`\`\`pm:${type}\n{"test":true}\n\`\`\``;
      const result = parsePMBlockMarkers(text);
      expect(result).toHaveLength(1);
      expect(result[0]!.type).toBe(type);
    }
  });

  it('ignores invalid pm block types', () => {
    const text = '```pm:unknown\n{"id":"x"}\n```';
    const result = parsePMBlockMarkers(text);
    expect(result).toHaveLength(0);
  });

  it('handles multi-line JSON content', () => {
    const text = ['```pm:raci', '{', '  "id": "r1",', '  "responsible": "alice"', '}', '```'].join(
      '\n'
    );

    const result = parsePMBlockMarkers(text);
    expect(result).toHaveLength(1);
    expect(result[0]!.type).toBe('raci');
    expect(result[0]!.startLine).toBe(1);
    expect(result[0]!.endLine).toBe(6);
    expect(result[0]!.data).toEqual({ id: 'r1', responsible: 'alice' });
  });

  it('handles empty content between markers', () => {
    const text = '```pm:form\n\n```';
    const result = parsePMBlockMarkers(text);
    expect(result).toHaveLength(1);
    expect(result[0]!.data).toBeNull();
    expect(result[0]!.raw).toBe('');
  });
});
