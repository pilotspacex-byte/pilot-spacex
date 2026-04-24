'use client';

/**
 * QuoteToChatPill — Phase 87 Plan 05 (ARTF-05).
 *
 * Floating pill that appears above a non-collapsed text selection inside the
 * note editor (`[data-tiptap-editor="note"]`). Click or ⌘J dispatches a
 * `pilot:quote-to-chat` CustomEvent that the chat composer's useQuoteToChat
 * hook turns into a quote block at the top of the draft.
 *
 * MUST be mounted as a SIBLING of IssueEditorContent (per .claude/rules/tiptap.md
 * — IssueEditorContent stays plain to avoid React 19 flushSync errors). The
 * component portals to `document.body` so it floats above editor chrome
 * without entering the editor's React subtree.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Sparkles } from 'lucide-react';

import type { QuoteEventDetail } from '@/hooks/use-quote-to-chat';

const MIN_QUOTE_CHARS = 4;
const MAX_QUOTE_CHARS = 600;
const SELECTION_DEBOUNCE_MS = 80;

export interface QuoteToChatPillProps {
  /** Source artifact id (note id) for the editor on this page. */
  sourceArtifactId: string;
  /** Fallback section label when no h1/h2/h3 precedes the selection. */
  artifactTitle: string;
  /**
   * Optional — invoked when the chat composer is not mounted. The pill queues
   * the event in `window.__pilotPendingQuotes` BEFORE calling this so the
   * composer's useQuoteToChat hook drains it on mount.
   */
  onEnsureChatMounted?: () => Promise<void> | void;
}

interface PillState {
  text: string;
  sectionLabel: string;
  rect: DOMRect;
}

function isInsideNoteEditor(node: Node | null): boolean {
  let cur: Node | null = node;
  while (cur) {
    if (
      cur.nodeType === 1 &&
      (cur as HTMLElement).getAttribute?.('data-tiptap-editor') === 'note'
    ) {
      return true;
    }
    cur = cur.parentNode;
  }
  return false;
}

function deriveSectionLabel(anchorNode: Node | null, fallback: string): string {
  let cur: Node | null = anchorNode;
  while (cur) {
    let prev: Node | null = cur.previousSibling;
    while (prev) {
      if (prev.nodeType === 1) {
        const el = prev as HTMLElement;
        if (/^H[1-3]$/.test(el.tagName)) {
          return el.textContent?.trim() || fallback;
        }
        const headings = el.querySelectorAll?.('h1, h2, h3');
        if (headings && headings.length > 0) {
          return headings[headings.length - 1]?.textContent?.trim() || fallback;
        }
      }
      prev = prev.previousSibling;
    }
    cur = cur.parentNode;
    // Stop walking once we leave the note editor — prevents the heuristic from
    // pulling content from the page header / sidebar (T-87-05-02 mitigation).
    if (
      cur &&
      cur.nodeType === 1 &&
      (cur as HTMLElement).getAttribute?.('data-tiptap-editor') === 'note'
    ) {
      break;
    }
  }
  return fallback;
}

export function QuoteToChatPill({
  sourceArtifactId,
  artifactTitle,
  onEnsureChatMounted,
}: QuoteToChatPillProps) {
  const [state, setState] = useState<PillState | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const evaluate = useCallback(() => {
    const sel = typeof window !== 'undefined' ? window.getSelection() : null;
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      setState(null);
      return;
    }
    const text = sel.toString().trim();
    if (text.length < MIN_QUOTE_CHARS || text.length > MAX_QUOTE_CHARS) {
      setState(null);
      return;
    }
    const range = sel.getRangeAt(0);
    if (!isInsideNoteEditor(range.commonAncestorContainer)) {
      setState(null);
      return;
    }
    const sectionLabel = deriveSectionLabel(sel.anchorNode, artifactTitle);
    // Defensive: JSDOM and some older browsers may lack Range.getBoundingClientRect.
    const rect =
      typeof range.getBoundingClientRect === 'function'
        ? range.getBoundingClientRect()
        : ({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 } as DOMRect);
    setState({ text, sectionLabel, rect });
  }, [artifactTitle]);

  // selectionchange listener (debounced 80ms)
  useEffect(() => {
    const handler = () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(evaluate, SELECTION_DEBOUNCE_MS);
    };
    document.addEventListener('selectionchange', handler);
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setState(null);
    };
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('selectionchange', handler);
      document.removeEventListener('keydown', onEsc);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [evaluate]);

  const dispatch = useCallback(async () => {
    if (!state) return;
    const detail: QuoteEventDetail = {
      text: state.text,
      sectionLabel: state.sectionLabel,
      sourceArtifactId,
      sourceArtifactType: 'NOTE',
    };
    const composerMounted =
      (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted ===
      true;
    if (!composerMounted && onEnsureChatMounted) {
      window.__pilotPendingQuotes = window.__pilotPendingQuotes ?? [];
      window.__pilotPendingQuotes.push(detail);
      await onEnsureChatMounted();
    } else {
      window.dispatchEvent(new CustomEvent('pilot:quote-to-chat', { detail }));
    }
    setState(null);
  }, [state, sourceArtifactId, onEnsureChatMounted]);

  // ⌘J / Ctrl+J shortcut while pill is visible
  useEffect(() => {
    if (!state) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        void dispatch();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [state, dispatch]);

  if (!state || typeof document === 'undefined') return null;

  return createPortal(
    <button
      type="button"
      role="button"
      aria-label="Ask AI about quoted text"
      data-quote-pill
      onMouseDown={(e) => {
        // Prevent the mousedown from collapsing the selection before our click.
        e.preventDefault();
      }}
      onClick={() => void dispatch()}
      className="fixed inline-flex items-center gap-2 h-7 px-3 rounded-full bg-white border border-[#29a386] shadow-sm hover:bg-[#29a386]/5 cursor-pointer motion-safe:animate-in motion-safe:fade-in motion-reduce:transition-none"
      style={{
        left: state.rect.right,
        top: state.rect.top - 8,
        transform: 'translate(-100%, -100%)',
        zIndex: 60,
      }}
    >
      <Sparkles className="h-3.5 w-3.5" style={{ color: '#29a386' }} />
      <span className="text-xs font-medium" style={{ color: '#1d7a63' }}>
        Ask AI about this
      </span>
      <kbd className="font-mono text-[10px] font-semibold text-muted-foreground rounded border border-border px-1 py-0.5 bg-input">
        ⌘J
      </kbd>
    </button>,
    document.body,
  );
}
