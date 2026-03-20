/**
 * FilePreviewModal tests — PREV-01, PREV-02, PREV-03, PREV-05
 *
 * Mocks:
 * - useFileContent hook — returns controlled content without network
 * - MarkdownContent — simple div for test isolation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FilePreviewModal } from '../FilePreviewModal';

// Mock useFileContent to avoid real network calls
vi.mock('../../hooks/useFileContent', () => ({
  useFileContent: vi.fn().mockReturnValue({
    content: 'mock content',
    isLoading: false,
    isError: false,
    isExpired: false,
  }),
}));

// Mock MarkdownContent for isolation
vi.mock('@/features/ai/ChatView/MessageList/MarkdownContent', () => ({
  MarkdownContent: ({ content }: { content: string }) => (
    <div data-testid="markdown-content">{content}</div>
  ),
}));

// Mock HtmlRenderer for isolation — prevents real iframe/DOMPurify from running in tests
vi.mock('../renderers/HtmlRenderer', () => ({
  HtmlRenderer: ({ content, filename }: { content: string; filename: string }) => (
    <div data-testid="html-renderer" data-filename={filename}>
      {content}
    </div>
  ),
}));

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  artifactId: 'artifact-1',
  filename: 'test-file.png',
  mimeType: 'image/png',
  signedUrl: 'https://example.com/file.png',
};

function renderModal(props = {}) {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <FilePreviewModal {...defaultProps} {...props} />
    </QueryClientProvider>
  );
}

describe('FilePreviewModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Header', () => {
    it('shows filename in the header', () => {
      renderModal({ filename: 'my-document.pdf', mimeType: 'application/pdf' });
      expect(screen.getByText('my-document.pdf')).toBeDefined();
    });

    it('shows download button pointing to signedUrl', () => {
      renderModal({ mimeType: 'application/pdf', filename: 'report.pdf' });
      const downloadLink = screen.getByRole('link', { name: /download file/i });
      expect(downloadLink).toBeDefined();
      expect(downloadLink.getAttribute('href')).toBe(defaultProps.signedUrl);
    });

    it('shows maximize button', () => {
      renderModal();
      expect(screen.getByRole('button', { name: /maximize/i })).toBeDefined();
    });

    it('resets isMaximized to false when modal re-opens', async () => {
      const { rerender } = renderModal();
      const client = makeClient();
      // Click maximize
      fireEvent.click(screen.getByRole('button', { name: /maximize/i }));
      // Verify maximize button changed to restore
      expect(screen.getByRole('button', { name: /restore size/i })).toBeDefined();
      // Close and reopen modal
      rerender(
        <QueryClientProvider client={client}>
          <FilePreviewModal {...defaultProps} open={false} />
        </QueryClientProvider>
      );
      rerender(
        <QueryClientProvider client={client}>
          <FilePreviewModal {...defaultProps} open={true} />
        </QueryClientProvider>
      );
      // After re-open, maximize button should be back
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /maximize/i })).toBeDefined();
      });
    });
  });

  describe('PREV-01: Image preview', () => {
    it('renders <img> tag when mimeType starts with image/', () => {
      renderModal({ mimeType: 'image/png', filename: 'photo.png' });
      expect(screen.getByRole('img')).toBeDefined();
    });

    it('clicking image toggles zoom state (cursor-zoom-in / cursor-zoom-out)', () => {
      renderModal({ mimeType: 'image/jpeg', filename: 'photo.jpg' });
      const img = screen.getByRole('img');
      const container = img.parentElement!;
      expect(container.className).toContain('cursor-zoom-in');
      fireEvent.click(container);
      expect(container.className).toContain('cursor-zoom-out');
    });

    it('img onError shows DownloadFallback with download link', () => {
      renderModal({ mimeType: 'image/png', filename: 'broken.png' });
      const img = screen.getByRole('img');
      fireEvent.error(img);
      // DownloadFallback with reason="expired" should show download link
      const downloadLink = screen.getByRole('link', { name: /download broken\.png/i });
      expect(downloadLink).toBeDefined();
    });
  });

  describe('PREV-02: Text, Markdown, JSON preview', () => {
    it('renders MarkdownContent for text/markdown MIME type', () => {
      renderModal({ mimeType: 'text/markdown', filename: 'README.md' });
      expect(screen.getByTestId('markdown-content')).toBeDefined();
    });

    it('renders <pre> block for plain text files (.txt)', () => {
      renderModal({ mimeType: 'text/plain', filename: 'notes.txt' });
      expect(screen.getByText('mock content').tagName).toBe('PRE');
    });

    it('renders JSON content as syntax-highlighted code block via MarkdownContent', () => {
      renderModal({ mimeType: 'application/json', filename: 'data.json' });
      const mdContent = screen.getByTestId('markdown-content');
      expect(mdContent).toBeDefined();
      // JsonRenderer wraps in ```json fenced block
      expect(mdContent.textContent).toContain('```json');
    });
  });

  describe('PREV-03: Code file preview', () => {
    it('detects Python from .py extension and uses CodeRenderer', () => {
      renderModal({ mimeType: 'text/plain', filename: 'main.py' });
      // CodeRenderer renders MarkdownContent with language fenced block
      const mdContent = screen.getByTestId('markdown-content');
      expect(mdContent.textContent).toContain('```python');
    });

    it('wraps code content in fenced block matching language', () => {
      renderModal({ mimeType: 'text/plain', filename: 'app.tsx' });
      const mdContent = screen.getByTestId('markdown-content');
      expect(mdContent.textContent).toContain('```typescript');
    });
  });

  describe('PREV-05: Download fallback', () => {
    it('renders DownloadFallback for application/pdf mimeType', () => {
      renderModal({ mimeType: 'application/pdf', filename: 'report.pdf' });
      // DownloadFallback shows download link
      expect(screen.getByRole('link', { name: /download report\.pdf/i })).toBeDefined();
    });

    it('renders DownloadFallback for application/octet-stream mimeType', () => {
      renderModal({ mimeType: 'application/octet-stream', filename: 'binary.bin' });
      expect(screen.getByRole('link', { name: /download binary\.bin/i })).toBeDefined();
    });

    it('renders HtmlRenderer for text/html with sandboxed preview', () => {
      renderModal({ mimeType: 'text/html', filename: 'page.html' });
      // Should render HtmlRenderer (sandboxed iframe + source toggle), not DownloadFallback
      const htmlRenderer = screen.getByTestId('html-renderer');
      expect(htmlRenderer).toBeDefined();
      expect(htmlRenderer.getAttribute('data-filename')).toBe('page.html');
      // Should NOT show DownloadFallback's link text pattern
      expect(screen.queryByRole('link', { name: /download page\.html/i })).toBeNull();
    });
  });
});
