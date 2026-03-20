import { describe, it, expect } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';
import { FileCardExtension } from '../file-card/FileCardExtension';

function makeEditor() {
  return new Editor({
    extensions: [
      StarterKit,
      Markdown.configure({ html: true, tightLists: true, breaks: false, linkify: false }),
      FileCardExtension,
    ],
  });
}

describe('FileCardExtension', () => {
  it('registers as a block node named "fileCard"', () => {
    const editor = makeEditor();
    expect(editor.schema.nodes.fileCard).toBeDefined();
    editor.destroy();
  });

  it('creates a fileCard node with default attrs', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'fileCard',
      attrs: {
        artifactId: 'test-uuid',
        filename: 'report.pdf',
        mimeType: 'application/pdf',
        sizeBytes: 1024,
        status: 'ready',
      },
    });
    const json = editor.getJSON();
    const node = json.content?.find((n) => n.type === 'fileCard');
    expect(node).toBeDefined();
    expect(node?.attrs?.artifactId).toBe('test-uuid');
    expect(node?.attrs?.filename).toBe('report.pdf');
    expect(node?.attrs?.status).toBe('ready');
    editor.destroy();
  });

  it('serializes fileCard to "[filename](artifact://uuid)" in markdown', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'fileCard',
      attrs: {
        artifactId: 'abc-123',
        filename: 'design.fig',
        mimeType: 'application/figma',
        sizeBytes: 2048,
        status: 'ready',
      },
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).toContain('[design.fig](artifact://abc-123)');
    editor.destroy();
  });

  it('omits uploading fileCard nodes from markdown (artifactId: null)', () => {
    const editor = makeEditor();
    editor.commands.insertContent({
      type: 'fileCard',
      attrs: {
        artifactId: null,
        filename: 'uploading.pdf',
        mimeType: 'application/pdf',
        sizeBytes: 0,
        status: 'uploading',
      },
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).not.toContain('artifact://');
    editor.destroy();
  });
});
