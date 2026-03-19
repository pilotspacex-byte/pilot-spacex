/**
 * YoutubeExtension tests
 *
 * VID-01: YouTube node inserts via setYoutubeVideo() command, markdown serializes as "[▶ YouTube](url)"
 * VID-04: YouTube renderHTML includes sandbox attribute
 *
 * RED phase: YoutubeExtension.ts does not exist yet — these tests will fail until Task 2.
 */
import { YoutubeExtension } from '../YoutubeExtension';
import { describe, it, expect, afterEach } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from 'tiptap-markdown';

function buildEditor(content?: object) {
  return new Editor({
    extensions: [StarterKit, Markdown.configure({ html: true }), YoutubeExtension],
    content: content ?? { type: 'doc', content: [] },
  });
}

describe('YoutubeExtension', () => {
  let editor: Editor;

  afterEach(() => {
    editor?.destroy();
  });

  it('VID-01: setYoutubeVideo produces [▶ YouTube] in markdown', () => {
    editor = buildEditor();
    editor.commands.setYoutubeVideo({
      src: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).toContain('[▶ YouTube]');
  });

  it('VID-04: YouTube iframe includes sandbox attribute containing "allow-scripts"', () => {
    editor = buildEditor();
    editor.commands.setYoutubeVideo({
      src: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    });
    const html = editor.getHTML();
    expect(html).toContain('sandbox');
    expect(html).toContain('allow-scripts');
  });

  it('VID-01 round-trip: getMarkdown() on YouTube node contains the original src URL', () => {
    editor = buildEditor();
    editor.commands.setYoutubeVideo({
      src: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const markdown = (editor.storage as any).markdown?.getMarkdown?.() ?? '';
    expect(markdown).toContain('dQw4w9WgXcQ');
  });
});
