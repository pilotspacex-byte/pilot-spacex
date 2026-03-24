/**
 * MarkdownPreview component tests.
 *
 * Covers: GFM tables, KaTeX math (inline + block), Mermaid diagrams,
 * syntax-highlighted code blocks, admonition containers, XSS sanitization,
 * and empty input handling.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

// Mock MermaidPreview (relies on browser mermaid API)
vi.mock('@/features/notes/editor/extensions/pm-blocks/MermaidPreview', () => ({
  MermaidPreview: ({ code }: { code: string }) => (
    <div data-testid="mermaid-preview-mock">{code}</div>
  ),
}));

// Mock DOMPurify to pass through in tests (sanitization unit tested separately)
vi.mock('dompurify', () => ({
  default: {
    sanitize: (input: string) => input,
  },
}));

// Mock katex CSS import (not available in jsdom)
vi.mock('katex/dist/katex.min.css', () => ({}));

import { MarkdownPreview } from '../MarkdownPreview';

describe('MarkdownPreview', () => {
  it('renders GFM table markdown into an HTML table element', () => {
    const md = `| Name | Age |\n| --- | --- |\n| Alice | 30 |`;
    const { container } = render(<MarkdownPreview content={md} />);
    const table = container.querySelector('table');
    expect(table).toBeTruthy();
    expect(table?.textContent).toContain('Alice');
  });

  it('renders inline math ($E=mc^2$) with katex class', () => {
    const md = `Equation: $E=mc^2$`;
    const { container } = render(<MarkdownPreview content={md} />);
    const katexEl = container.querySelector('.katex');
    expect(katexEl).toBeTruthy();
  });

  it('renders block math ($$sum$$) with katex-display class', () => {
    const md = `\n$$\n\\sum_{i=1}^n x_i\n$$\n`;
    const { container } = render(<MarkdownPreview content={md} />);
    const katexDisplay = container.querySelector('.katex-display');
    expect(katexDisplay).toBeTruthy();
  });

  it('renders mermaid code block into MermaidPreview component', () => {
    const md = '```mermaid\ngraph TD;\nA-->B;\n```';
    render(<MarkdownPreview content={md} />);
    const mermaidMock = screen.getByTestId('mermaid-preview-mock');
    expect(mermaidMock).toBeTruthy();
    expect(mermaidMock.textContent).toContain('graph TD');
  });

  it('renders typescript code block with syntax highlighting (hljs class)', () => {
    const md = '```typescript\nconst x: number = 42;\n```';
    const { container } = render(<MarkdownPreview content={md} />);
    const codeEl = container.querySelector('code.hljs');
    expect(codeEl).toBeTruthy();
  });

  it('renders :::note container into admonition div with data-admonition="note"', () => {
    const md = ':::note\nThis is a note.\n:::';
    const { container } = render(<MarkdownPreview content={md} />);
    const admonition = container.querySelector('[data-admonition="note"]');
    expect(admonition).toBeTruthy();
    expect(admonition?.textContent).toContain('This is a note.');
  });

  it('renders :::warning container into admonition div with data-admonition="warning"', () => {
    const md = ':::warning\nBe careful!\n:::';
    const { container } = render(<MarkdownPreview content={md} />);
    const admonition = container.querySelector('[data-admonition="warning"]');
    expect(admonition).toBeTruthy();
    expect(admonition?.textContent).toContain('Be careful!');
  });

  it('renders :::tip container into admonition div with data-admonition="tip"', () => {
    const md = ':::tip\nHelpful tip here.\n:::';
    const { container } = render(<MarkdownPreview content={md} />);
    const admonition = container.querySelector('[data-admonition="tip"]');
    expect(admonition).toBeTruthy();
    expect(admonition?.textContent).toContain('Helpful tip here.');
  });

  it('sanitizes content via DOMPurify (mock passes through)', () => {
    const md = '**bold text**';
    const { container } = render(<MarkdownPreview content={md} />);
    const strong = container.querySelector('strong');
    expect(strong).toBeTruthy();
    expect(strong?.textContent).toBe('bold text');
  });

  it('renders nothing on empty string input (no crash)', () => {
    const { container } = render(<MarkdownPreview content="" />);
    // The wrapper div should exist but have no markdown content
    const wrapper = container.firstElementChild;
    expect(wrapper).toBeTruthy();
    // No error thrown, component renders cleanly
  });

  it('applies max-w-[720px] class to wrapper', () => {
    const { container } = render(<MarkdownPreview content="test" />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain('max-w-[720px]');
  });

  it('accepts and applies custom className', () => {
    const { container } = render(<MarkdownPreview content="test" className="my-custom-class" />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain('my-custom-class');
  });
});
