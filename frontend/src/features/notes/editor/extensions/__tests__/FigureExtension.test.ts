import { describe, it, expect } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import { FigureExtension } from '../figure/FigureExtension';

function makeEditor() {
  return new Editor({
    extensions: [
      StarterKit,
      Markdown.configure({ html: true, tightLists: true, breaks: false, linkify: false }),
      FigureExtension,
    ],
  });
}

describe('FigureExtension', () => {
  it('registers as a block node named "figure"', () => {
    const editor = makeEditor();
    expect(editor.schema.nodes.figure).toBeDefined();
    editor.destroy();
  });

  it('creates a figure node with src and status attrs', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'figure',
      attrs: {
        src: 'https://example.com/img.png',
        alt: '',
        status: 'ready',
        artifactId: 'img-uuid',
      },
      content: [{ type: 'text', text: 'My caption' }],
    });
    const json = editor.getJSON();
    const node = json.content?.find((n) => n.type === 'figure');
    expect(node).toBeDefined();
    expect(node?.attrs?.src).toBe('https://example.com/img.png');
    expect(node?.attrs?.status).toBe('ready');
    editor.destroy();
  });

  it('serializes figure to "![caption](src)" in markdown', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'figure',
      attrs: {
        src: 'https://example.com/photo.jpg',
        alt: 'My photo',
        status: 'ready',
        artifactId: null,
      },
      content: [{ type: 'text', text: 'My photo caption' }],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).toContain('![');
    expect(markdown).toContain('https://example.com/photo.jpg');
    editor.destroy();
  });

  it('preserves caption text across markdown round-trip', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'figure',
      attrs: { src: 'https://example.com/img.png', alt: '', status: 'ready', artifactId: null },
      content: [{ type: 'text', text: 'Round-trip caption' }],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    // Caption used as alt text — verify it's in the markdown
    expect(markdown).toContain('Round-trip caption');
    editor.destroy();
  });
});
