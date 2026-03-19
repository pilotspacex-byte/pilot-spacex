/**
 * FilePreviewModal tests — PREV-01, PREV-02, PREV-03, PREV-05
 *
 * Full implementation added in Plan 02 after components are built.
 * These scaffolds define the required behaviors — they ensure Plan 02 ships
 * with test coverage rather than discovering it's missing after the fact.
 *
 * Run state: all tests are .todo — they will show as pending (yellow) in CI,
 * not failing. Plan 02 will replace .todo with full implementations.
 */
import { describe, it } from 'vitest';

describe('FilePreviewModal', () => {
  describe('PREV-01: Image preview', () => {
    it.todo('renders <img> tag when mimeType starts with image/');
    it.todo('clicking image toggles zoom state (cursor-zoom-in / cursor-zoom-out)');
    it.todo('img onError shows DownloadFallback with reason="expired"');
  });

  describe('PREV-02: Text, Markdown, JSON preview', () => {
    it.todo('renders MarkdownContent for text/markdown MIME type');
    it.todo('renders <pre> block for plain text files (.txt)');
    it.todo('renders JSON content as syntax-highlighted code block via MarkdownContent');
  });

  describe('PREV-03: Code file preview', () => {
    it.todo('detects Python from .py extension and passes language=python to CodeRenderer');
    it.todo('wraps code content in fenced block: ```python\\n{code}\\n```');
  });

  describe('PREV-05: Download fallback', () => {
    it.todo('renders DownloadFallback for application/pdf mimeType');
    it.todo('renders DownloadFallback for application/octet-stream mimeType');
    it.todo('download button has correct href pointing to signedUrl');
  });
});
