/**
 * Unit tests for useNoteHealth hook.
 *
 * @module hooks/__tests__/useNoteHealth.test
 * @see T020-T022
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNoteHealth, countActionableVerbs } from '../useNoteHealth';
import type { LinkedIssueBrief } from '@/types';

// Mock getAIStore
const mockGetAnnotationsForNote = vi.fn().mockReturnValue([]);
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: () => ({
    marginAnnotation: {
      getAnnotationsForNote: mockGetAnnotationsForNote,
    },
  }),
}));

/** Create a mock TipTap editor with specified paragraph texts */
function createMockEditor(paragraphs: string[]) {
  const nodes = paragraphs.map((text) => ({
    type: { name: 'paragraph' },
    textContent: text,
    attrs: {},
  }));

  const updateHandlers: Array<() => void> = [];

  return {
    isDestroyed: false,
    state: {
      doc: {
        forEach: (cb: (node: { type: { name: string }; textContent: string }) => void) => {
          nodes.forEach(cb);
        },
        textContent: paragraphs.join('\n'),
      },
    },
    on: (event: string, handler: () => void) => {
      if (event === 'update') updateHandlers.push(handler);
    },
    off: (event: string, handler: () => void) => {
      if (event === 'update') {
        const idx = updateHandlers.indexOf(handler);
        if (idx >= 0) updateHandlers.splice(idx, 1);
      }
    },
    /** Helper to simulate content update */
    _triggerUpdate: () => {
      updateHandlers.forEach((h) => h());
    },
    /** Helper to change content */
    _setContent: (newParagraphs: string[]) => {
      nodes.length = 0;
      newParagraphs.forEach((text) => {
        nodes.push({ type: { name: 'paragraph' }, textContent: text, attrs: {} });
      });
      // Update textContent reference
      Object.defineProperty(
        (createMockEditor as unknown as { _lastEditor: unknown })._lastEditor,
        'state',
        {
          value: {
            doc: {
              forEach: (cb: (node: { type: { name: string }; textContent: string }) => void) => {
                nodes.forEach(cb);
              },
              textContent: newParagraphs.join('\n'),
            },
          },
          configurable: true,
        }
      );
    },
  } as unknown as import('@tiptap/core').Editor;
}

const LINKED_ISSUES: LinkedIssueBrief[] = [
  {
    id: '1',
    identifier: 'PS-42',
    name: 'Fix login bug',
    priority: 'high' as const,
    state: { id: 's1', name: 'In Progress', group: 'started', color: '#000' },
  },
  {
    id: '2',
    identifier: 'PS-55',
    name: 'Add dark mode',
    priority: 'medium' as const,
    state: { id: 's2', name: 'Todo', group: 'unstarted', color: '#999' },
  },
];

describe('countActionableVerbs', () => {
  it('returns 0 for empty text', () => {
    expect(countActionableVerbs('')).toBe(0);
  });

  it('returns 0 for text without actionable verbs', () => {
    expect(countActionableVerbs('The quick brown fox jumps over the lazy dog')).toBe(0);
  });

  it('counts single actionable verb', () => {
    expect(countActionableVerbs('We need to implement the login flow')).toBe(1);
  });

  it('counts multiple actionable verbs', () => {
    expect(countActionableVerbs('Implement the auth module and fix the login bug')).toBe(2);
  });

  it('is case-insensitive', () => {
    expect(countActionableVerbs('IMPLEMENT this and FIX that')).toBe(2);
  });

  it('counts all known verbs', () => {
    const text = 'implement fix add create update remove build design refactor test deploy migrate';
    expect(countActionableVerbs(text)).toBe(12);
  });
});

describe('useNoteHealth', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockGetAnnotationsForNote.mockReturnValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('computes extractableCount from editor paragraphs', () => {
    const editor = createMockEditor([
      'We need to implement the auth and fix the login',
      'Just a regular paragraph',
      'Create the dashboard and deploy it',
    ]);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    // 2 paragraphs have 2+ actionable verbs
    expect(result.current.extractableCount).toBe(2);
  });

  it('returns 0 extractableCount for paragraphs with fewer than 2 verbs', () => {
    const editor = createMockEditor(['Implement the login flow', 'No actionable items here']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));
    expect(result.current.extractableCount).toBe(0);
  });

  it('reads clarity issues from MarginAnnotationStore', () => {
    mockGetAnnotationsForNote.mockReturnValue([
      { id: 'a1', type: 'question', status: 'pending' },
      { id: 'a2', type: 'warning', status: 'pending' },
      { id: 'a3', type: 'suggestion', status: 'pending' },
      { id: 'a4', type: 'question', status: 'accepted' },
    ]);

    const editor = createMockEditor(['Some content']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    // Only pending question + warning count
    expect(result.current.clarityIssueCount).toBe(2);
  });

  it('passes through linkedIssues', () => {
    const editor = createMockEditor(['Some content']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, LINKED_ISSUES));

    expect(result.current.linkedIssues).toBe(LINKED_ISSUES);
    expect(result.current.linkedIssues).toHaveLength(2);
  });

  it('generates extractable prompt when extractableCount > 0', () => {
    const editor = createMockEditor(['Implement the auth and fix the login']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    expect(result.current.suggestedPrompts).toContain('Extract 1 actionable item as issues');
  });

  it('generates clarity prompt when clarityIssueCount > 0', () => {
    mockGetAnnotationsForNote.mockReturnValue([{ id: 'a1', type: 'question', status: 'pending' }]);

    const editor = createMockEditor(['Some content']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    expect(result.current.suggestedPrompts).toContain('Improve clarity in 1 section');
  });

  it('generates linked issues prompt when linkedIssues > 0', () => {
    const editor = createMockEditor(['Some content']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, LINKED_ISSUES));

    expect(result.current.suggestedPrompts).toContain('Summarize progress on 2 linked issues');
  });

  it('generates fallback prompt when no issues found', () => {
    const editor = createMockEditor(['No actionable content here']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    expect(result.current.suggestedPrompts).toContain('Analyze this note for improvements');
  });

  it('handles null editor gracefully', () => {
    const { result } = renderHook(() => useNoteHealth('note-1', null, []));

    expect(result.current.extractableCount).toBe(0);
    expect(result.current.clarityIssueCount).toBe(0);
    expect(result.current.isComputing).toBe(false);
  });

  it('debounces recomputation on editor update', () => {
    const editor = createMockEditor(['Implement and fix the auth']);

    const { result } = renderHook(() => useNoteHealth('note-1', editor, []));

    expect(result.current.extractableCount).toBe(1);

    // Simulate content change via update event
    // The actual recomputation is debounced by 5000ms
    act(() => {
      (editor as unknown as { _triggerUpdate: () => void })._triggerUpdate();
    });

    // Before debounce fires, count stays the same
    expect(result.current.extractableCount).toBe(1);

    // Advance past debounce
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    // After debounce, recomputed (same content so same count)
    expect(result.current.extractableCount).toBe(1);
  });

  it('recomputes immediately on noteId change', () => {
    const editor = createMockEditor(['Implement and fix the auth']);

    const { result, rerender } = renderHook(({ noteId }) => useNoteHealth(noteId, editor, []), {
      initialProps: { noteId: 'note-1' },
    });

    expect(result.current.extractableCount).toBe(1);

    // Change noteId
    rerender({ noteId: 'note-2' });

    // Immediate recomputation (no debounce)
    expect(result.current.extractableCount).toBe(1);
  });
});
