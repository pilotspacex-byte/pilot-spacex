/**
 * Tests for useQuoteToChat hook — Phase 87 Plan 05 (ARTF-05).
 */
import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRef } from 'react';
import type { RefObject } from 'react';

import { useQuoteToChat, type QuoteEventDetail } from '../use-quote-to-chat';

function dispatchQuote(detail: QuoteEventDetail) {
  window.dispatchEvent(new CustomEvent('pilot:quote-to-chat', { detail }));
}

function makeDetail(text = 'hello', sectionLabel = 'Section'): QuoteEventDetail {
  return {
    text,
    sectionLabel,
    sourceArtifactId: 'A1',
    sourceArtifactType: 'NOTE',
  };
}

function makeMockEditor() {
  const insertContentAt = vi.fn();
  const focus = vi.fn();
  const run = vi.fn();
  const chain = vi.fn(() => ({
    focus: () => {
      focus();
      return {
        insertContentAt: (pos: number, content: unknown) => {
          insertContentAt(pos, content);
          return { run };
        },
      };
    },
  }));
  return { chain, insertContentAt, focus, run };
}

describe('useQuoteToChat', () => {
  beforeEach(() => {
    delete window.__pilotPendingQuotes;
  });

  afterEach(() => {
    delete window.__pilotPendingQuotes;
  });

  it('Test 1: dispatched event triggers TipTap insertContentAt(0, quoteBlock)', () => {
    const ed = makeMockEditor();
    renderHook(() => useQuoteToChat(ed as unknown as Parameters<typeof useQuoteToChat>[0]));
    dispatchQuote(makeDetail('quoted'));
    expect(ed.insertContentAt).toHaveBeenCalledWith(0, {
      type: 'quoteBlock',
      attrs: { text: 'quoted', sectionLabel: 'Section', sourceArtifactId: 'A1' },
    });
    expect(ed.run).toHaveBeenCalled();
  });

  it('Test 2: drains __pilotPendingQuotes on mount and clears the queue', () => {
    window.__pilotPendingQuotes = [makeDetail('first'), makeDetail('second')];
    const ed = makeMockEditor();
    renderHook(() => useQuoteToChat(ed as unknown as Parameters<typeof useQuoteToChat>[0]));
    expect(ed.insertContentAt).toHaveBeenCalledTimes(2);
    expect(window.__pilotPendingQuotes).toEqual([]);
  });

  it('Test 3: null editor does NOT throw', () => {
    expect(() => renderHook(() => useQuoteToChat(null))).not.toThrow();
    // dispatch should be a no-op
    expect(() => dispatchQuote(makeDetail())).not.toThrow();
  });

  it('Test 4: removes listener on unmount', () => {
    const ed = makeMockEditor();
    const { unmount } = renderHook(() =>
      useQuoteToChat(ed as unknown as Parameters<typeof useQuoteToChat>[0]),
    );
    unmount();
    dispatchQuote(makeDetail('after-unmount'));
    expect(ed.insertContentAt).not.toHaveBeenCalled();
  });

  it('Test 5: multiple events insert in order', () => {
    const ed = makeMockEditor();
    renderHook(() => useQuoteToChat(ed as unknown as Parameters<typeof useQuoteToChat>[0]));
    dispatchQuote(makeDetail('one'));
    dispatchQuote(makeDetail('two'));
    dispatchQuote(makeDetail('three'));
    expect(ed.insertContentAt).toHaveBeenCalledTimes(3);
    expect(ed.insertContentAt.mock.calls[0]?.[1]).toMatchObject({ attrs: { text: 'one' } });
    expect(ed.insertContentAt.mock.calls[2]?.[1]).toMatchObject({ attrs: { text: 'three' } });
  });

  it('Test 6: TipTap path focuses the editor (chain().focus()) before insert', () => {
    const ed = makeMockEditor();
    renderHook(() => useQuoteToChat(ed as unknown as Parameters<typeof useQuoteToChat>[0]));
    dispatchQuote(makeDetail());
    // chain() was called — insert path goes through chain().focus().insertContentAt
    expect(ed.chain).toHaveBeenCalled();
  });

  it('Test 7: contentEditable target prepends quote block + calls onChange', () => {
    const div = document.createElement('div');
    const initialChild = document.createTextNode('user typing');
    div.appendChild(initialChild);
    const ref: RefObject<HTMLDivElement | null> = createRef<HTMLDivElement | null>();
    // Force the ref to point at our div for the test
    Object.defineProperty(ref, 'current', { value: div, writable: true });
    const onChange = vi.fn();

    renderHook(() => useQuoteToChat({ ref, onChange }));
    dispatchQuote(makeDetail('quoted body', 'Section'));

    // First child should now be the quote block, original text node should remain second
    expect(div.firstElementChild?.getAttribute('data-quote-block')).not.toBeNull();
    expect(div.firstElementChild?.getAttribute('data-section-label')).toBe('Section');
    expect(onChange).toHaveBeenCalledTimes(1);
  });
});
