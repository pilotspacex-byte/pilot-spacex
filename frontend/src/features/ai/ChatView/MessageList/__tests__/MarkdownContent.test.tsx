/**
 * Unit tests for MarkdownContent streaming fade-in effect.
 *
 * Tests static rendering, streaming fade-in animation on new content,
 * stable content without animation, cursor at end, and empty content.
 *
 * @module features/ai/ChatView/MessageList/__tests__/MarkdownContent
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act } from '@testing-library/react';

// Mock react-markdown to render plain text (avoids ESM/remark issues in tests)
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <span data-testid="markdown">{children}</span>,
}));

vi.mock('remark-gfm', () => ({ default: () => {} }));
vi.mock('rehype-highlight', () => ({ default: () => {} }));

import { MarkdownContent } from '../MarkdownContent';

/** Tailwind variant class as rendered in DOM */
const FADE_CLASS = 'motion-safe:animate-fade-up';

/** Query helper: querySelector can't handle colons, use attribute selector */
function queryFadeElements(container: HTMLElement): Element[] {
  return Array.from(container.querySelectorAll('span')).filter((el) =>
    el.className.includes('animate-fade-up')
  );
}

describe('MarkdownContent', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

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

  it('renders content without animation wrappers when isStreaming is false', () => {
    const { container } = render(
      <MarkdownContent content="Hello world\nSecond line" isStreaming={false} />
    );

    const fadeElements = queryFadeElements(container);
    expect(fadeElements).toHaveLength(0);

    expect(container.textContent).toContain('Hello world');
    expect(container.textContent).toContain('Second line');
  });

  it('does not render streaming cursor when isStreaming is false', () => {
    const { container } = render(<MarkdownContent content="Hello world" isStreaming={false} />);

    // Cursor uses animate-pulse + bg-primary
    const cursors = Array.from(container.querySelectorAll('span')).filter(
      (el) => el.className.includes('animate-pulse') && el.className.includes('bg-primary')
    );
    expect(cursors).toHaveLength(0);
  });

  // ========================================
  // Streaming: latest content has fade animation
  // ========================================

  it('applies fade animation class to new content when isStreaming is true', () => {
    const { container } = render(<MarkdownContent content="First line" isStreaming />);

    const fadeElements = queryFadeElements(container);
    expect(fadeElements).toHaveLength(1);
    expect(fadeElements[0]!.className).toContain(FADE_CLASS);
  });

  // ========================================
  // Streaming: stable content has no animation
  // ========================================

  it('renders previously seen content without animation after split point update', () => {
    const { container, rerender } = render(<MarkdownContent content="Line one\n" isStreaming />);

    // Let the timer fire to advance split point (200ms)
    act(() => {
      vi.advanceTimersByTime(250);
    });

    // Rerender with new content appended
    rerender(<MarkdownContent content="Line one\nLine two" isStreaming />);

    // Should have exactly one animated wrapper (for new content)
    const fadeElements = queryFadeElements(container);
    expect(fadeElements).toHaveLength(1);

    // The animated part should contain the new content
    expect(fadeElements[0]!.textContent).toContain('Line two');

    // Stable part: first markdown element should NOT be wrapped in a fade span
    const markdownElements = container.querySelectorAll('[data-testid="markdown"]');
    const stableMarkdown = markdownElements[0];
    // Walk up from stableMarkdown -- no ancestor should have the fade class
    let ancestor: Element | null = stableMarkdown?.parentElement ?? null;
    let stableHasFadeAncestor = false;
    while (ancestor && ancestor !== container) {
      if (ancestor.className?.includes('animate-fade-up')) {
        stableHasFadeAncestor = true;
        break;
      }
      ancestor = ancestor.parentElement;
    }
    expect(stableHasFadeAncestor).toBe(false);
    expect(stableMarkdown?.textContent).toContain('Line one');
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

  // ========================================
  // Reset on streaming end
  // ========================================

  it('removes animation wrappers when isStreaming transitions to false', () => {
    const { container, rerender } = render(
      <MarkdownContent content="Streaming text" isStreaming />
    );

    // Should have animated content
    expect(queryFadeElements(container)).toHaveLength(1);

    // Stop streaming
    rerender(<MarkdownContent content="Streaming text" isStreaming={false} />);

    // No animation wrappers should remain
    expect(queryFadeElements(container)).toHaveLength(0);
  });

  // ========================================
  // displayName
  // ========================================

  it('exports MarkdownContent with displayName', () => {
    expect(MarkdownContent.displayName).toBe('MarkdownContent');
  });
});
