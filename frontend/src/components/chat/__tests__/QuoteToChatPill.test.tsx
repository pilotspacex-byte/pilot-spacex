/**
 * Tests for QuoteToChatPill — Phase 87 Plan 05 (ARTF-05).
 *
 * JSDOM caveat: range.getBoundingClientRect() returns zeros and
 * selectionchange does not fire automatically on programmatic selection
 * mutation. Tests dispatch the event manually after building a Range.
 */
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { QuoteToChatPill } from '../QuoteToChatPill';

const DEFAULT_PROPS = {
  sourceArtifactId: 'NOTE-1',
  artifactTitle: 'My Note',
};

function clearBody() {
  while (document.body.firstChild) document.body.removeChild(document.body.firstChild);
}

function makeNoteEditorWithText(text: string) {
  const root = document.createElement('div');
  root.setAttribute('data-tiptap-editor', 'note');
  const p = document.createElement('p');
  p.textContent = text;
  root.appendChild(p);
  document.body.appendChild(root);
  return { root, p };
}

function makeNonNoteContainerWithText(text: string) {
  const root = document.createElement('div');
  const p = document.createElement('p');
  p.textContent = text;
  root.appendChild(p);
  document.body.appendChild(root);
  return { root, p };
}

function selectNodeContents(node: Node) {
  const range = document.createRange();
  range.selectNodeContents(node);
  const sel = window.getSelection();
  if (!sel) throw new Error('No selection');
  sel.removeAllRanges();
  sel.addRange(range);
  document.dispatchEvent(new Event('selectionchange'));
}

async function tickDebounce() {
  await act(async () => {
    vi.advanceTimersByTime(100);
  });
}

describe('QuoteToChatPill', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    clearBody();
    delete (window as unknown as { __pilotPendingQuotes?: unknown }).__pilotPendingQuotes;
    delete (window as unknown as { __pilotChatComposerMounted?: boolean })
      .__pilotChatComposerMounted;
  });

  afterEach(() => {
    vi.useRealTimers();
    // Note: do NOT call clearBody() here. RTL auto-cleanup unmounts the
    // portaled pill from document.body; manual removal races and throws
    // NotFoundError in JSDOM.
  });

  it('Test 1: with no selection, pill is NOT in the DOM', async () => {
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    await tickDebounce();
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 2: 3-char selection (below threshold) does NOT show pill', async () => {
    const { p } = makeNoteEditorWithText('abc');
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 3: 10-char selection inside note editor SHOWS pill after debounce', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    expect(screen.getByLabelText(/ask ai about quoted text/i)).toBeInTheDocument();
  });

  it('Test 4: 700-char selection (above ceiling) does NOT show pill', async () => {
    const { p } = makeNoteEditorWithText('x'.repeat(700));
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 5: selection in container WITHOUT data-tiptap-editor="note" does NOT show pill', async () => {
    const { p } = makeNonNoteContainerWithText('valid text outside');
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 5b: selection in a contentEditable WITHOUT note attribute (e.g. ChatInput) does NOT show pill', async () => {
    const root = document.createElement('div');
    root.setAttribute('contenteditable', 'true');
    root.textContent = 'chat input typing';
    document.body.appendChild(root);
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(root);
    await tickDebounce();
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 6: clicking pill dispatches pilot:quote-to-chat with the expected detail', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    const listener = vi.fn();
    window.addEventListener('pilot:quote-to-chat', listener as EventListener);
    (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted =
      true;

    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();

    const pill = screen.getByLabelText(/ask ai about quoted text/i);
    await act(async () => {
      pill.click();
    });

    expect(listener).toHaveBeenCalledTimes(1);
    const detail = (listener.mock.calls[0]?.[0] as CustomEvent).detail as Record<string, unknown>;
    expect(detail.text).toBe('valid text');
    expect(detail.sourceArtifactId).toBe('NOTE-1');
    expect(detail.sourceArtifactType).toBe('NOTE');
    expect(typeof detail.sectionLabel).toBe('string');

    window.removeEventListener('pilot:quote-to-chat', listener as EventListener);
  });

  it('Test 7: ⌘J dispatches the same event', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    const listener = vi.fn();
    window.addEventListener('pilot:quote-to-chat', listener as EventListener);
    (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted =
      true;

    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();

    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', metaKey: true }));
    });

    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener('pilot:quote-to-chat', listener as EventListener);
  });

  it('Test 8: after dispatch, the pill hides', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted =
      true;

    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    const pill = screen.getByLabelText(/ask ai about quoted text/i);

    await act(async () => {
      pill.click();
    });
    expect(screen.queryByLabelText(/ask ai about quoted text/i)).not.toBeInTheDocument();
  });

  it('Test 9: sectionLabel resolves to nearest preceding h2', async () => {
    const root = document.createElement('div');
    root.setAttribute('data-tiptap-editor', 'note');
    const h2 = document.createElement('h2');
    h2.textContent = 'My Section';
    const p = document.createElement('p');
    p.textContent = 'valid text';
    root.appendChild(h2);
    root.appendChild(p);
    document.body.appendChild(root);

    const listener = vi.fn();
    window.addEventListener('pilot:quote-to-chat', listener as EventListener);
    (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted =
      true;

    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    const pill = screen.getByLabelText(/ask ai about quoted text/i);
    await act(async () => {
      pill.click();
    });

    const detail = (listener.mock.calls[0]?.[0] as CustomEvent).detail as Record<string, unknown>;
    expect(detail.sectionLabel).toBe('My Section');

    window.removeEventListener('pilot:quote-to-chat', listener as EventListener);
  });

  it('Test 9b: sectionLabel falls back to artifactTitle when no preceding heading', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    const listener = vi.fn();
    window.addEventListener('pilot:quote-to-chat', listener as EventListener);
    (window as unknown as { __pilotChatComposerMounted?: boolean }).__pilotChatComposerMounted =
      true;

    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();
    const pill = screen.getByLabelText(/ask ai about quoted text/i);
    await act(async () => {
      pill.click();
    });

    const detail = (listener.mock.calls[0]?.[0] as CustomEvent).detail as Record<string, unknown>;
    expect(detail.sectionLabel).toBe('My Note');

    window.removeEventListener('pilot:quote-to-chat', listener as EventListener);
  });

  it('Test 10: pill has data-quote-pill attribute, role=button, and aria-label', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    render(<QuoteToChatPill {...DEFAULT_PROPS} />);
    selectNodeContents(p);
    await tickDebounce();

    const pill = screen.getByLabelText(/ask ai about quoted text/i);
    expect(pill.getAttribute('data-quote-pill')).not.toBeNull();
    expect(pill.getAttribute('role')).toBe('button');
    expect(pill.getAttribute('aria-label')).toBe('Ask AI about quoted text');
  });

  it('Test 11: queues to __pilotPendingQuotes when composer not mounted', async () => {
    const { p } = makeNoteEditorWithText('valid text');
    const ensureMounted = vi.fn().mockResolvedValue(undefined);

    render(<QuoteToChatPill {...DEFAULT_PROPS} onEnsureChatMounted={ensureMounted} />);
    selectNodeContents(p);
    await tickDebounce();

    const pill = screen.getByLabelText(/ask ai about quoted text/i);
    await act(async () => {
      pill.click();
    });

    expect(ensureMounted).toHaveBeenCalledTimes(1);
    expect(window.__pilotPendingQuotes).toBeDefined();
    expect(window.__pilotPendingQuotes?.length).toBe(1);
    expect(window.__pilotPendingQuotes?.[0]?.text).toBe('valid text');
  });
});
