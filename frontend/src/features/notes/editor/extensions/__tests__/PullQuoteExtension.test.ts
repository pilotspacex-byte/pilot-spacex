/**
 * PullQuoteExtension tests
 *
 * EDIT-01: User can toggle pull quote styling on blockquotes.
 * Tests: attribute toggle, markdown serialization (> [!quote]), round-trip, blockId assignment.
 *
 * RED phase: PullQuoteExtension.ts does not exist yet (Plan 02 creates it).
 * These tests will fail until Plan 02 completes.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import { PullQuoteExtension } from '../PullQuoteExtension';
import { BlockIdExtension } from '../BlockIdExtension';

/** Build a minimal editor with PullQuoteExtension — isolated from full extension stack */
function buildEditor(content?: object) {
  return new Editor({
    extensions: [
      StarterKit.configure({ blockquote: false }),
      Markdown.configure({ html: true, tightLists: true }),
      PullQuoteExtension,
      BlockIdExtension,
    ],
    content: content ?? { type: 'doc', content: [] },
  });
}

describe('PullQuoteExtension', () => {
  let editor: Editor;

  afterEach(() => {
    editor?.destroy();
  });

  it('test_pull_quote_attr_true_set_on_blockquote_node', () => {
    editor = buildEditor();
    editor.commands.insertContent({
      type: 'blockquote',
      attrs: { pullQuote: true },
      content: [
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'Editorial quote text' }],
        },
      ],
    });
    const json = editor.getJSON();
    const blockquote = json.content?.find((n) => n.type === 'blockquote');
    expect(blockquote).toBeDefined();
    expect(blockquote?.attrs?.pullQuote).toBe(true);
  });

  it('test_pull_quote_markdown_serialize_outputs_gfm_callout', () => {
    editor = buildEditor({
      type: 'doc',
      content: [
        {
          type: 'blockquote',
          attrs: { pullQuote: true },
          content: [
            {
              type: 'paragraph',
              content: [{ type: 'text', text: 'A pull quote' }],
            },
          ],
        },
      ],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown() as string;
    expect(markdown).toContain('> [!quote]');
  });

  it('test_standard_blockquote_serializes_as_plain_blockquote', () => {
    editor = buildEditor({
      type: 'doc',
      content: [
        {
          type: 'blockquote',
          attrs: { pullQuote: false },
          content: [
            {
              type: 'paragraph',
              content: [{ type: 'text', text: 'A plain quote' }],
            },
          ],
        },
      ],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown() as string;
    expect(markdown).not.toContain('[!quote]');
    expect(markdown).toContain('>');
  });

  it('test_pull_quote_round_trip_markdown_survives_re_parse', () => {
    // Step 1: Create editor with pull quote
    editor = buildEditor({
      type: 'doc',
      content: [
        {
          type: 'blockquote',
          attrs: { pullQuote: true },
          content: [
            {
              type: 'paragraph',
              content: [{ type: 'text', text: 'Round-trip quote' }],
            },
          ],
        },
      ],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown() as string;
    editor.destroy();

    // Step 2: Re-parse the markdown in a fresh editor
    const editor2 = buildEditor(markdown as unknown as object);
    const json2 = editor2.getJSON();
    const blockquote = json2.content?.find((n) => n.type === 'blockquote');
    expect(blockquote).toBeDefined();
    // After round-trip, pull quote attr should survive
    expect(blockquote?.attrs?.pullQuote).toBe(true);
    editor2.destroy();
  });

  it('test_block_id_assigned_to_pull_quote_node', () => {
    editor = buildEditor();
    editor.commands.insertContent({
      type: 'blockquote',
      attrs: { pullQuote: true },
      content: [
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'Quote with blockId' }],
        },
      ],
    });
    const json = editor.getJSON();
    const blockquote = json.content?.find((n) => n.type === 'blockquote');
    expect(blockquote?.attrs?.blockId).toBeTruthy();
    // Should be UUID format (8-4-4-4-12 hex chars)
    expect(blockquote?.attrs?.blockId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });
});
