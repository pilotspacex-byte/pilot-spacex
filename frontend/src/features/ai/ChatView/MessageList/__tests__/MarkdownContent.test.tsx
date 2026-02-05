/**
 * Unit tests for MarkdownContent component.
 *
 * Tests static rendering, streaming fade-in animation on container,
 * cursor at end during streaming, and empty content.
 *
 * @module features/ai/ChatView/MessageList/__tests__/MarkdownContent
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

// Mock react-markdown to render plain text (avoids ESM/remark issues in tests)
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <span data-testid="markdown">{children}</span>,
}));

vi.mock('remark-gfm', () => ({ default: () => {} }));
vi.mock('rehype-highlight', () => ({ default: () => {} }));

import { MarkdownContent } from '../MarkdownContent';

/** Tailwind variant class as rendered in DOM */
const FADE_CLASS = 'animate-fade-up';

describe('MarkdownContent', () => {
  // ========================================
  // Empty content
  // ========================================

  it('returns null when content is empty', () => {
    const { container } = render(<MarkdownContent content="" />);
    expect(container.firstElementChild).toBeNull();
  });

  // ========================================
  // Static rendering (isStreaming=false)
  // ========================================

  it('renders content without animation when isStreaming is false', () => {
    const { container } = render(
      <MarkdownContent content="Hello world\nSecond line" isStreaming={false} />
    );

    // Container div should NOT have fade-up class
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).not.toContain(FADE_CLASS);

    expect(container.textContent).toContain('Hello world');
    expect(container.textContent).toContain('Second line');
  });

  it('does not render streaming cursor when isStreaming is false', () => {
    const { container } = render(<MarkdownContent content="Hello world" isStreaming={false} />);

    const cursors = Array.from(container.querySelectorAll('span')).filter(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-primary')
    );
    expect(cursors).toHaveLength(0);
  });

  // ========================================
  // Streaming: container has fade animation
  // ========================================

  it('applies fade animation class to container when isStreaming is true', () => {
    const { container } = render(<MarkdownContent content="First line" isStreaming />);

    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain(FADE_CLASS);
  });

  it('renders all content in a single ReactMarkdown instance during streaming', () => {
    const { container } = render(
      <MarkdownContent content="Line one\nLine two\nLine three" isStreaming />
    );

    // Should have exactly one markdown element (single render, not split)
    const markdownElements = container.querySelectorAll('[data-testid="markdown"]');
    expect(markdownElements).toHaveLength(1);
    expect(markdownElements[0]!.textContent).toContain('Line one');
    expect(markdownElements[0]!.textContent).toContain('Line three');
  });

  // ========================================
  // Streaming: cursor renders at end
  // ========================================

  it('renders streaming cursor at the end when isStreaming is true', () => {
    const { container } = render(<MarkdownContent content="Some streaming text" isStreaming />);

    const cursors = Array.from(container.querySelectorAll('span')).filter(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-primary')
    );
    expect(cursors).toHaveLength(1);
  });

  it('cursor has aria-hidden for accessibility', () => {
    const { container } = render(<MarkdownContent content="Text" isStreaming />);

    const cursor = Array.from(container.querySelectorAll('span')).find(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-primary')
    );
    expect(cursor?.getAttribute('aria-hidden')).toBe('true');
  });

  // ========================================
  // Reset on streaming end
  // ========================================

  it('removes animation and cursor when isStreaming transitions to false', () => {
    const { container, rerender } = render(
      <MarkdownContent content="Streaming text" isStreaming />
    );

    // Should have animated container
    expect(container.firstElementChild?.className).toContain(FADE_CLASS);

    // Stop streaming
    rerender(<MarkdownContent content="Streaming text" isStreaming={false} />);

    // No animation on container
    expect(container.firstElementChild?.className).not.toContain(FADE_CLASS);

    // No cursor
    const cursors = Array.from(container.querySelectorAll('span')).filter(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-primary')
    );
    expect(cursors).toHaveLength(0);
  });

  // ========================================
  // displayName
  // ========================================

  it('exports MarkdownContent with displayName', () => {
    expect(MarkdownContent.displayName).toBe('MarkdownContent');
  });
});
