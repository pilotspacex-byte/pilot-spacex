import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  generateFullContextMarkdown,
  generateSectionMarkdown,
  copyToClipboard,
  type AIContextResultForCopy,
} from '../copy-context';

const createTestData = (overrides?: Partial<AIContextResultForCopy>): AIContextResultForCopy => ({
  summary: {
    issueIdentifier: 'PS-42',
    title: 'Test issue',
    summaryText: 'Test summary',
    stats: { relatedCount: 1, docsCount: 1, filesCount: 0, tasksCount: 1 },
  },
  relatedIssues: [
    {
      relationType: 'blocks',
      issueId: 'issue-1',
      identifier: 'PS-40',
      title: 'Related',
      summary: 'Summary',
      status: 'Done',
      stateGroup: 'completed',
    },
  ],
  relatedDocs: [{ docType: 'ADR', title: 'Doc', summary: 'Doc summary' }],
  tasks: [{ id: 1, title: 'Task', estimate: '3 points', dependencies: [], completed: false }],
  prompts: [{ taskId: 1, title: 'Task', content: 'Prompt content' }],
  ...overrides,
});

describe('copy-context', () => {
  describe('generateFullContextMarkdown', () => {
    it('should generate markdown with all sections', () => {
      const markdown = generateFullContextMarkdown(
        createTestData({
          tasks: [{ id: 1, title: 'Task', estimate: '3', dependencies: [2], completed: false }],
        })
      );

      expect(markdown).toContain('# PS-42: Test issue');
      expect(markdown).toContain('## Summary\nTest summary');
      expect(markdown).toContain('## Related Issues');
      expect(markdown).toContain('PS-40 (blocks): Related — Done');
      expect(markdown).toContain('## Related Documents');
      expect(markdown).toContain('[ADR] Doc');
      expect(markdown).toContain('## Implementation Tasks');
      expect(markdown).toContain('Dependencies: 2');
      expect(markdown).toContain('## Ready-to-Use Prompts');
      expect(markdown).toContain('### Task 1: Task');
    });

    it('should generate minimal markdown with empty arrays', () => {
      const result = createTestData({
        relatedIssues: [],
        relatedDocs: [],
        tasks: [],
        prompts: [],
      });

      expect(generateFullContextMarkdown(result)).toBe(
        '# PS-42: Test issue\n\n## Summary\nTest summary'
      );
    });

    it('should generate fallback heading when summary is null', () => {
      const result = createTestData({
        summary: null,
        relatedIssues: [],
        relatedDocs: [],
        tasks: [],
        prompts: [],
      });
      expect(generateFullContextMarkdown(result)).toBe('# AI Context');
    });
  });

  describe('generateSectionMarkdown', () => {
    const testData = createTestData();

    it('should generate summary section', () => {
      expect(generateSectionMarkdown('summary', testData)).toBe('Test summary');
    });

    it('should generate related_issues section', () => {
      const md = generateSectionMarkdown('related_issues', testData);
      expect(md).toContain('PS-40 (blocks): Related — Done');
    });

    it('should generate related_docs section', () => {
      const md = generateSectionMarkdown('related_docs', testData);
      expect(md).toContain('[ADR] Doc');
    });

    it('should generate tasks section', () => {
      expect(generateSectionMarkdown('tasks', testData)).toBe('1. Task (3 points)');
    });

    it('should generate prompts section', () => {
      const md = generateSectionMarkdown('prompts', testData);
      expect(md).toContain('### Task 1: Task');
      expect(md).toContain('```\nPrompt content\n```');
    });

    it('should return empty string for unknown section or empty data', () => {
      expect(generateSectionMarkdown('invalid', testData)).toBe('');
      const empty = createTestData({
        summary: null,
        relatedIssues: [],
        relatedDocs: [],
        tasks: [],
        prompts: [],
      });
      expect(generateSectionMarkdown('summary', empty)).toBe('');
      expect(generateSectionMarkdown('related_issues', empty)).toBe('');
    });
  });

  describe('copyToClipboard', () => {
    beforeEach(() => {
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn(),
        },
      });
    });

    it('should return true when clipboard write succeeds', async () => {
      vi.mocked(navigator.clipboard.writeText).mockResolvedValue();

      const result = await copyToClipboard('test content');

      expect(result).toBe(true);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test content');
    });

    it('should return false when clipboard write fails', async () => {
      vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error('Clipboard error'));

      const result = await copyToClipboard('test content');

      expect(result).toBe(false);
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test content');
    });
  });
});
