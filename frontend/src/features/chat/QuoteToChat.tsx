'use client';

/**
 * QuoteToChat — floating chip that appears at the end of a text selection and
 * lets the user "quote" the selection into the chat composer as a markdown
 * blockquote.
 *
 * Scope: only activates when the selection's common ancestor is inside a
 * `[data-quote-scope]` element (note editor, chat messages, peek drawer body).
 * This prevents the chip from appearing for selections in sidebars/menus.
 *
 * Trigger: click on chip OR ⌘J / Ctrl+J shortcut.
 *
 * Side effect: dispatches a `pilot:quote-to-chat` CustomEvent with
 * `{ text: string, source?: string }`. The chat composer listens for this
 * event and appends a blockquote to the current input value. A shared event
 * bus avoids coupling QuoteToChat to any specific store.
 *
 * Phase 4 coordination: this component does not care where the selection
 * originates — peek drawer, note editor, or chat message all work the same
 * way via `[data-quote-scope]`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MessageSquareQuote } from 'lucide-react';
import { cn } from '@/lib/utils';

export const QUOTE_TO_CHAT_EVENT = 'pilot:quote-to-chat' as const;

export interface QuoteToChatEventDetail {
  text: string;
  source?: string;
}

/** Dispatch helper for tests and programmatic quoting. */
export function dispatchQuoteToChat(detail: QuoteToChatEventDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(QUOTE_TO_CHAT_EVENT, { detail }));
}

interface ChipPosition {
  top: number;
  left: number;
}

/** Returns true when `node` is inside a [data-quote-scope] element. */
function isInQuoteScope(node: Node | null): boolean {
  let current: Node | null = node;
  while (current) {
    if (current instanceof HTMLElement && current.hasAttribute('data-quote-scope')) {
      return true;
    }
    current = current.parentNode;
  }
  return false;
}

/** Get the source name from the nearest [data-quote-scope] ancestor. */
function getQuoteSource(node: Node | null): string | undefined {
  let current: Node | null = node;
  while (current) {
    if (current instanceof HTMLElement && current.hasAttribute('data-quote-scope')) {
      return current.getAttribute('data-quote-scope') || undefined;
    }
    current = current.parentNode;
  }
  return undefined;
}

export function QuoteToChat() {
  const [mounted, setMounted] = useState(false);
  const [position, setPosition] = useState<ChipPosition | null>(null);
  const [selectedText, setSelectedText] = useState<string>('');
  const [source, setSource] = useState<string | undefined>(undefined);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const chipRef = useRef<HTMLButtonElement>(null);

  // Mount guard — portal into document.body, which does not exist during SSR.
  // Also observe `prefers-reduced-motion` and keep it as state so the chip's
  // transition class reacts to system preference changes.
  /* eslint-disable react-hooks/set-state-in-effect -- one-shot mount + media-query sync */
  useEffect(() => {
    setMounted(true);
    if (typeof window === 'undefined' || !('matchMedia' in window)) return;
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mql.matches);
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener('change', listener);
    return () => mql.removeEventListener('change', listener);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const hideChip = useCallback(() => {
    setPosition(null);
    setSelectedText('');
    setSource(undefined);
  }, []);

  const updateChipFromSelection = useCallback(() => {
    if (typeof window === 'undefined') return;
    const selection = window.getSelection();

    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      hideChip();
      return;
    }

    const text = selection.toString().trim();
    if (!text) {
      hideChip();
      return;
    }

    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;

    if (!isInQuoteScope(container)) {
      hideChip();
      return;
    }

    // Ignore selections that live inside the chat composer itself — quoting
    // would feed back into the source.
    const composerSelector = '[data-composer-scope]';
    let anchor: Node | null = container;
    while (anchor) {
      if (
        anchor instanceof HTMLElement &&
        anchor.matches?.(composerSelector)
      ) {
        hideChip();
        return;
      }
      anchor = anchor.parentNode;
    }

    const rects = range.getClientRects();
    const lastRect = rects.length > 0 ? rects[rects.length - 1] : range.getBoundingClientRect();
    if (!lastRect || (lastRect.width === 0 && lastRect.height === 0)) {
      hideChip();
      return;
    }

    // Position the chip just below the end of the selection's last line.
    const GAP = 8;
    setPosition({
      top: lastRect.bottom + GAP + window.scrollY,
      left: Math.max(8, lastRect.right + window.scrollX - 140),
    });
    setSelectedText(text);
    setSource(getQuoteSource(container));
  }, [hideChip]);

  // Listen for selection changes globally.
  useEffect(() => {
    if (typeof document === 'undefined') return;

    let rafId: number | null = null;
    const scheduleUpdate = () => {
      if (rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        rafId = null;
        updateChipFromSelection();
      });
    };

    document.addEventListener('selectionchange', scheduleUpdate);
    window.addEventListener('scroll', scheduleUpdate, true);
    window.addEventListener('resize', scheduleUpdate);

    return () => {
      document.removeEventListener('selectionchange', scheduleUpdate);
      window.removeEventListener('scroll', scheduleUpdate, true);
      window.removeEventListener('resize', scheduleUpdate);
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, [updateChipFromSelection]);

  const handleQuote = useCallback(() => {
    if (!selectedText) return;
    dispatchQuoteToChat({ text: selectedText, source });
    // Clear the native selection so the chip disappears.
    window.getSelection()?.removeAllRanges();
    hideChip();
  }, [selectedText, source, hideChip]);

  // ⌘J / Ctrl+J keyboard shortcut — active whenever a chip is visible.
  useEffect(() => {
    if (!position || !selectedText) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        hideChip();
        return;
      }
      const isModifier = event.metaKey || event.ctrlKey;
      if (isModifier && event.key.toLowerCase() === 'j') {
        event.preventDefault();
        handleQuote();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [position, selectedText, handleQuote, hideChip]);

  // Close the chip on outside click (but not when clicking the chip itself).
  useEffect(() => {
    if (!position) return;

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (chipRef.current?.contains(target)) return;
      // Defer so selectionchange can update position first.
      requestAnimationFrame(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) hideChip();
      });
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [position, hideChip]);

  if (!mounted || !position || !selectedText) return null;

  const chip = (
    <button
      ref={chipRef}
      type="button"
      aria-label="Quote selection in chat"
      onClick={handleQuote}
      // Use onMouseDown to prevent the click from clearing the selection
      // before onClick reads it.
      onMouseDown={(e) => e.preventDefault()}
      style={{
        position: 'absolute',
        top: position.top,
        left: position.left,
        zIndex: 60,
      }}
      className={cn(
        'inline-flex items-center gap-2 rounded-full',
        'border border-[var(--border-toolbar)] bg-card text-foreground',
        'px-3 py-1.5 text-xs font-medium shadow-md',
        'hover:bg-accent hover:text-accent-foreground',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-1',
        !prefersReducedMotion && 'transition-colors'
      )}
    >
      <MessageSquareQuote className="h-3.5 w-3.5" aria-hidden="true" />
      <span>Quote in chat</span>
      <kbd className="inline-flex items-center gap-0.5 rounded-full border border-border/60 bg-muted/60 px-1.5 py-0.5 font-mono text-[10px] leading-none text-muted-foreground">
        <span aria-hidden="true">⌘</span>J
      </kbd>
    </button>
  );

  return createPortal(chip, document.body);
}

QuoteToChat.displayName = 'QuoteToChat';
