/**
 * VimeoNode tests
 *
 * VID-02: extractVimeoId() handles vimeo.com/id and player.vimeo.com/video/id patterns
 * VID-03: isVideoUrl() returns correct platform label or null
 * VID-04: VimeoNode renderHTML includes sandbox attribute
 *
 * RED phase: VimeoNode.ts does not exist yet — these tests will fail until Task 2.
 */
import { VimeoNode, extractVimeoId, isVideoUrl } from '../VimeoNode';
import { describe, it, expect, afterEach } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';

function buildEditor(content?: object) {
  return new Editor({
    extensions: [StarterKit, Markdown.configure({ html: true }), VimeoNode],
    content: content ?? { type: 'doc', content: [] },
  });
}

describe('extractVimeoId', () => {
  it('VID-02: extracts ID from vimeo.com/id URL', () => {
    expect(extractVimeoId('https://vimeo.com/123456789')).toBe('123456789');
  });

  it('VID-02: extracts ID from player.vimeo.com/video/id URL', () => {
    expect(extractVimeoId('https://player.vimeo.com/video/987654321')).toBe('987654321');
  });

  it('VID-02: returns null for non-Vimeo URL', () => {
    expect(extractVimeoId('https://notvimeo.com/123')).toBeNull();
  });
});

describe('isVideoUrl', () => {
  it('VID-03: returns "youtube" for youtube.com URL', () => {
    expect(isVideoUrl('https://www.youtube.com/watch?v=abc')).toBe('youtube');
  });

  it('VID-03: returns "youtube" for youtu.be short URL', () => {
    expect(isVideoUrl('https://youtu.be/abc')).toBe('youtube');
  });

  it('VID-03: returns "vimeo" for vimeo.com URL', () => {
    expect(isVideoUrl('https://vimeo.com/123')).toBe('vimeo');
  });

  it('VID-03: returns null for unknown domain', () => {
    expect(isVideoUrl('https://example.com')).toBeNull();
  });
});

describe('VimeoNode', () => {
  let editor: Editor;

  afterEach(() => {
    editor?.destroy();
  });

  it('VID-04: VimeoNode renderHTML includes sandbox attribute', () => {
    // Access renderHTML from the node config directly
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = (VimeoNode as any).config.renderHTML({ HTMLAttributes: {} });
    // result is ['iframe', { sandbox: '...', ... }]
    expect(result[1]).toMatchObject({
      sandbox: 'allow-scripts allow-same-origin allow-presentation allow-fullscreen',
    });
  });

  it('VID-02 round-trip: insert vimeo node, getMarkdown() contains "[▶ Vimeo]"', () => {
    editor = buildEditor();
    editor.commands.insertContent({
      type: 'vimeo',
      attrs: { src: 'https://player.vimeo.com/video/123456789' },
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).toContain('[▶ Vimeo]');
  });
});
