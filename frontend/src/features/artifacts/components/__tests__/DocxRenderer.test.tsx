/**
 * DocxRenderer tests — DOCX-01, DOCX-02, DOCX-03, DOCX-04
 *
 * Tests dual-engine rendering (docx-preview primary, mammoth fallback),
 * sandboxed iframe isolation, heading extraction, and error states.
 *
 * NOTE: DocxRenderer uses dynamic imports for docx-preview and mammoth.
 * We mock these at the module level and test the component's rendered output.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// Mock DOMPurify — pass through HTML for test inspection
vi.mock('dompurify', () => ({
  default: {
    sanitize: vi.fn((html: string) => html),
  },
}));

// Mock docx-preview — renders HTML into the temp container
const mockRenderAsync = vi.fn();
vi.mock('docx-preview', () => ({
  renderAsync: (...args: unknown[]) => mockRenderAsync(...args),
}));

// Mock mammoth — returns HTML string
const mockConvertToHtml = vi.fn();
const mockImgElement = vi.fn((cb: unknown) => cb);
vi.mock('mammoth', () => ({
  default: {
    convertToHtml: (...args: unknown[]) => mockConvertToHtml(...args),
    images: { imgElement: (cb: unknown) => mockImgElement(cb) },
  },
  convertToHtml: (...args: unknown[]) => mockConvertToHtml(...args),
  images: { imgElement: (cb: unknown) => mockImgElement(cb) },
}));

// Import AFTER mocks are registered
import { DocxRenderer } from '../renderers/DocxRenderer';

const sampleBuffer = new ArrayBuffer(8);

const defaultProps = {
  content: sampleBuffer,
  filename: 'document.docx',
  signedUrl: 'https://example.com/document.docx',
};

describe('DocxRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('DOCX-01: shows loading spinner while rendering', () => {
    // Mock renderAsync to never resolve (keeps component in loading state)
    mockRenderAsync.mockReturnValue(new Promise(() => {}));

    render(<DocxRenderer {...defaultProps} />);

    const spinner = screen.getByRole('status', { name: /rendering document/i });
    expect(spinner).toBeDefined();
  });

  it('DOCX-01: renders iframe with sandbox="allow-same-origin" after docx-preview succeeds', async () => {
    // Mock renderAsync: sets content on the temporary container via DOM API
    mockRenderAsync.mockImplementation(async (_data: ArrayBuffer, container: HTMLElement) => {
      const p = container.ownerDocument.createElement('p');
      p.textContent = 'Hello DOCX';
      container.appendChild(p);
    });

    render(<DocxRenderer {...defaultProps} />);

    await waitFor(() => {
      const iframe = document.querySelector('iframe');
      expect(iframe).not.toBeNull();
    });

    const iframe = document.querySelector('iframe');
    expect(iframe).not.toBeNull();
    expect(iframe!.getAttribute('sandbox')).toBe('allow-same-origin');
    expect(iframe!.getAttribute('srcdoc')).toContain('Hello DOCX');
  });

  it('DOCX-02: falls back to mammoth when docx-preview fails', async () => {
    // docx-preview fails
    mockRenderAsync.mockRejectedValue(new Error('docx-preview failed'));

    // mammoth succeeds
    mockConvertToHtml.mockResolvedValue({
      value: '<h1>Mammoth Output</h1><p>Fallback content</p>',
      messages: [],
    });

    render(<DocxRenderer {...defaultProps} />);

    await waitFor(() => {
      const iframe = document.querySelector('iframe');
      expect(iframe).not.toBeNull();
      expect(iframe!.getAttribute('srcdoc')).toContain('Mammoth Output');
    });

    // Verify render mode is mammoth
    const container = document.querySelector('[data-render-mode="mammoth"]');
    expect(container).not.toBeNull();
  });

  it('DOCX-02: shows DownloadFallback when both engines fail', async () => {
    // Both fail
    mockRenderAsync.mockRejectedValue(new Error('docx-preview failed'));
    mockConvertToHtml.mockRejectedValue(new Error('mammoth failed'));

    render(<DocxRenderer {...defaultProps} />);

    await waitFor(() => {
      // DownloadFallback renders a download link
      const downloadLink = screen.getByRole('link', { name: /download document\.docx/i });
      expect(downloadLink).toBeDefined();
    });
  });

  it('DOCX-01: iframe does not contain allow-scripts in sandbox', async () => {
    mockRenderAsync.mockImplementation(async (_data: ArrayBuffer, container: HTMLElement) => {
      const p = container.ownerDocument.createElement('p');
      p.textContent = 'Content';
      container.appendChild(p);
    });

    render(<DocxRenderer {...defaultProps} />);

    await waitFor(() => {
      const iframe = document.querySelector('iframe');
      expect(iframe).not.toBeNull();
    });

    const iframe = document.querySelector('iframe');
    const sandbox = iframe!.getAttribute('sandbox') ?? '';
    expect(sandbox).not.toContain('allow-scripts');
  });

  it('DOCX-04: extracts headings from rendered document for ToC sidebar', async () => {
    mockRenderAsync.mockImplementation(async (_data: ArrayBuffer, container: HTMLElement) => {
      const doc = container.ownerDocument;
      const h1 = doc.createElement('h1');
      h1.textContent = 'Chapter 1';
      const p = doc.createElement('p');
      p.textContent = 'Text';
      const h2 = doc.createElement('h2');
      h2.textContent = 'Section 1.1';
      const h3 = doc.createElement('h3');
      h3.textContent = 'Subsection';
      container.append(h1, p, h2, h3);
    });

    render(<DocxRenderer {...defaultProps} tocOpen />);

    await waitFor(() => {
      // DocxTocSidebar should render heading buttons
      const chapter1 = screen.getByRole('button', { name: 'Chapter 1' });
      expect(chapter1).toBeDefined();
    });

    expect(screen.getByRole('button', { name: 'Section 1.1' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Subsection' })).toBeDefined();
  });

  it('DOCX-04: ToC sidebar is hidden when tocOpen is false', async () => {
    mockRenderAsync.mockImplementation(async (_data: ArrayBuffer, container: HTMLElement) => {
      const h1 = container.ownerDocument.createElement('h1');
      h1.textContent = 'Heading';
      container.appendChild(h1);
    });

    render(<DocxRenderer {...defaultProps} tocOpen={false} />);

    await waitFor(() => {
      const iframe = document.querySelector('iframe');
      expect(iframe).not.toBeNull();
    });

    // ToC sidebar should not be in the DOM
    const sidebar = document.querySelector('[aria-label="Table of contents"]');
    expect(sidebar).toBeNull();
  });

  it('iframe has accessible title containing filename', async () => {
    mockRenderAsync.mockImplementation(async (_data: ArrayBuffer, container: HTMLElement) => {
      const p = container.ownerDocument.createElement('p');
      p.textContent = 'Content';
      container.appendChild(p);
    });

    render(<DocxRenderer {...defaultProps} />);

    await waitFor(() => {
      const iframe = document.querySelector('iframe');
      expect(iframe).not.toBeNull();
    });

    const iframe = document.querySelector('iframe');
    const title = iframe!.getAttribute('title') ?? '';
    expect(title).toContain('document.docx');
  });

  it('shows error state for empty content', async () => {
    const emptyBuffer = new ArrayBuffer(0);

    render(<DocxRenderer {...defaultProps} content={emptyBuffer} />);

    await waitFor(() => {
      const downloadLink = screen.getByRole('link', { name: /download document\.docx/i });
      expect(downloadLink).toBeDefined();
    });
  });
});
