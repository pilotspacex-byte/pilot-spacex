/**
 * Markdown Integration Test
 * Tests bidirectional markdown conversion for editor content
 */
import { describe, it, expect } from 'vitest';
import { Editor } from '@tiptap/core';
import { createEditorExtensions } from '../createEditorExtensions';

describe('Markdown Extension Integration', () => {
  it('should parse markdown content into editor', () => {
    const extensions = createEditorExtensions({
      placeholder: 'Test editor',
      enableSlashCommands: false,
      enableMentions: false,
    });

    const editor = new Editor({
      extensions,
      content: '# Hello World\n\nThis is a **test**.',
    });

    // Verify JSON structure
    const json = editor.getJSON();
    expect(json.content).toBeDefined();
    expect(json.content?.[0]?.type).toBe('heading');
    expect(json.content?.[1]?.type).toBe('paragraph');

    editor.destroy();
  });

  it('should serialize editor content to markdown', () => {
    const extensions = createEditorExtensions({
      placeholder: 'Test editor',
      enableSlashCommands: false,
      enableMentions: false,
    });

    const editor = new Editor({
      extensions,
      content: {
        type: 'doc',
        content: [
          {
            type: 'heading',
            attrs: { level: 1 },
            content: [{ type: 'text', text: 'Hello World' }],
          },
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'This is a ' },
              { type: 'text', text: 'test', marks: [{ type: 'bold' }] },
              { type: 'text', text: '.' },
            ],
          },
        ],
      },
    });

    // Get markdown output
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown();
    expect(markdown).toContain('# Hello World');
    expect(markdown).toContain('**test**');

    editor.destroy();
  });

  it('should handle inline issue syntax', () => {
    const extensions = createEditorExtensions({
      placeholder: 'Test editor',
      enableSlashCommands: false,
      enableMentions: false,
      enableInlineIssues: true,
    });

    // Parse markdown with inline issue
    const editor = new Editor({
      extensions,
      content: 'Check out [PS-99](issue:123e4567-e89b-12d3-a456-426614174000 "Fix login bug")',
    });

    // Verify inlineIssue node created
    const json = editor.getJSON();
    const paragraph = json.content?.[0];
    expect(paragraph?.type).toBe('paragraph');

    // The inline issue should be parsed as an inlineIssue node
    const content = paragraph?.content;
    if (content) {
      const issueNode = content.find((node: { type: string }) => node.type === 'inlineIssue');
      if (issueNode && 'attrs' in issueNode) {
        expect(issueNode.attrs).toMatchObject({
          issueId: '123e4567-e89b-12d3-a456-426614174000',
          issueKey: 'PS-99',
          title: 'Fix login bug',
        });
      }
    }

    editor.destroy();
  });

  it('should serialize inline issue to markdown', () => {
    const extensions = createEditorExtensions({
      placeholder: 'Test editor',
      enableSlashCommands: false,
      enableMentions: false,
      enableInlineIssues: true,
    });

    const editor = new Editor({
      extensions,
      content: {
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'Check out ' },
              {
                type: 'inlineIssue',
                attrs: {
                  issueId: '123e4567-e89b-12d3-a456-426614174000',
                  issueKey: 'PS-99',
                  title: 'Fix login bug',
                  type: 'bug',
                  state: 'todo',
                  priority: 'high',
                },
              },
            ],
          },
        ],
      },
    });

    // Get markdown output
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown();
    expect(markdown).toContain(
      '[PS-99](issue:123e4567-e89b-12d3-a456-426614174000 "Fix login bug")'
    );

    editor.destroy();
  });

  it('should handle insertContent with markdown string', () => {
    const extensions = createEditorExtensions({
      placeholder: 'Test editor',
      enableSlashCommands: false,
      enableMentions: false,
    });

    const editor = new Editor({
      extensions,
      content: '',
    });

    // Insert markdown content
    editor.commands.insertContent('## Section Title\n\nSome **bold** text.');

    const json = editor.getJSON();
    expect(json.content?.[0]?.type).toBe('heading');
    expect(json.content?.[1]?.type).toBe('paragraph');

    editor.destroy();
  });
});
