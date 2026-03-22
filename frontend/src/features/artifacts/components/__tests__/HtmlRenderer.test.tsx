/**
 * HtmlRenderer tests — HTML-02, HTML-03, HTML-04, HTML-06
 *
 * Tests sandboxed iframe preview, source/preview toggle, and accessibility.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock DOMPurify — return HTML as-is so tests can inspect rendered content
vi.mock('dompurify', () => ({
  default: {
    sanitize: vi.fn((html: string) => html),
  },
}));

// Mock MarkdownContent for isolation (same as FilePreviewModal.test.tsx)
vi.mock('@/features/ai/ChatView/MessageList/MarkdownContent', () => ({
  MarkdownContent: ({ content }: { content: string }) => (
    <div data-testid="markdown-content">{content}</div>
  ),
}));

// Import AFTER mocks are registered
import { HtmlRenderer } from '../renderers/HtmlRenderer';

const defaultProps = {
  content: '<h1>Hello</h1>',
  filename: 'test.html',
};

describe('HtmlRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('HTML-03: default (source) mode renders CodeRenderer with language="html"', () => {
    render(<HtmlRenderer {...defaultProps} />);
    // CodeRenderer uses MarkdownContent with ```html fenced block
    const mdContent = screen.getByTestId('markdown-content');
    expect(mdContent).toBeDefined();
    expect(mdContent.textContent).toContain('```html');
  });

  it('HTML-02: preview mode renders an iframe with srcdoc attribute', () => {
    render(<HtmlRenderer {...defaultProps} />);
    // Click Preview tab to switch to preview mode
    const previewTab = screen.getByRole('tab', { name: /preview/i });
    fireEvent.click(previewTab);
    const iframe = document.querySelector('iframe');
    expect(iframe).not.toBeNull();
    expect(iframe!.getAttribute('srcdoc')).not.toBeNull();
  });

  it('HTML-06: iframe sandbox attribute does NOT contain "allow-scripts"', () => {
    render(<HtmlRenderer {...defaultProps} />);
    const previewTab = screen.getByRole('tab', { name: /preview/i });
    fireEvent.click(previewTab);
    const iframe = document.querySelector('iframe');
    expect(iframe).not.toBeNull();
    const sandbox = iframe!.getAttribute('sandbox') ?? '';
    expect(sandbox).not.toContain('allow-scripts');
  });

  it('HTML-02: iframe has empty sandbox (maximum isolation, no allow-same-origin)', () => {
    render(<HtmlRenderer {...defaultProps} />);
    const previewTab = screen.getByRole('tab', { name: /preview/i });
    fireEvent.click(previewTab);
    const iframe = document.querySelector('iframe');
    expect(iframe).not.toBeNull();
    expect(iframe!.getAttribute('sandbox')).toBe('');
  });

  it('HTML-04: clicking "Preview" tab switches from source to preview mode (iframe appears)', () => {
    render(<HtmlRenderer {...defaultProps} />);
    // Initially in source mode — no iframe
    expect(document.querySelector('iframe')).toBeNull();
    // Click Preview
    const previewTab = screen.getByRole('tab', { name: /preview/i });
    fireEvent.click(previewTab);
    // Now in preview mode — iframe appears
    expect(document.querySelector('iframe')).not.toBeNull();
  });

  it('clicking "Source" tab switches back to source mode (CodeRenderer appears, iframe gone)', () => {
    render(<HtmlRenderer {...defaultProps} />);
    // Switch to preview
    fireEvent.click(screen.getByRole('tab', { name: /preview/i }));
    expect(document.querySelector('iframe')).not.toBeNull();
    // Switch back to source
    fireEvent.click(screen.getByRole('tab', { name: /source/i }));
    expect(document.querySelector('iframe')).toBeNull();
    expect(screen.getByTestId('markdown-content')).toBeDefined();
  });

  it('iframe has a title attribute containing the filename for accessibility', () => {
    render(<HtmlRenderer {...defaultProps} />);
    fireEvent.click(screen.getByRole('tab', { name: /preview/i }));
    const iframe = document.querySelector('iframe');
    expect(iframe).not.toBeNull();
    const title = iframe!.getAttribute('title') ?? '';
    expect(title).toContain('test.html');
  });

  it('DOMPurify config forbids style, link, base, and meta tags', async () => {
    render(<HtmlRenderer {...defaultProps} />);
    fireEvent.click(screen.getByRole('tab', { name: /preview/i }));
    // Access the mock via dynamic import (ESM-compatible)
    const dompurify = await import('dompurify');
    const sanitizeFn = dompurify.default.sanitize as ReturnType<typeof vi.fn>;
    expect(sanitizeFn).toHaveBeenCalled();
    const config = sanitizeFn.mock.calls[0]?.[1] as
      | {
          FORBID_TAGS?: string[];
          FORBID_ATTR?: string[];
        }
      | undefined;
    expect(config?.FORBID_TAGS).toContain('style');
    expect(config?.FORBID_TAGS).toContain('link');
    expect(config?.FORBID_TAGS).toContain('base');
    expect(config?.FORBID_TAGS).toContain('meta');
    expect(config?.FORBID_ATTR).toContain('style');
  });
});
