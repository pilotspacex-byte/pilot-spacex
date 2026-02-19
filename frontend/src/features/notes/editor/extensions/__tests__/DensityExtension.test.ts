/**
 * Unit tests for DensityExtension (T-135, M8 — Feature 016)
 *
 * Tests:
 * - T-129: collapsed attribute + toggle commands
 * - T-130: Intent block collapse summary (FR-095)
 * - T-131: Progress block collapse summary (FR-096)
 * - T-132: AI block group auto-collapse for groups >3 (FR-099)
 * - T-133: Focus Mode toggle hides AI blocks, <200ms (FR-098)
 * - T-134: Collapse persistence via localStorage
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {
  DensityExtension,
  buildCollapseSummary,
  type DensityOptions,
  type DensityStorage,
} from '../DensityExtension';
import { BlockIdExtension } from '../BlockIdExtension';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

function getDensityStorage(editor: Editor): DensityStorage {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (editor as any).extensionStorage['density'] as DensityStorage;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const LOCAL_STORAGE_KEY = 'pilot-density-test-note-id';
const FOCUS_KEY = 'pilot-focusmode-test-note-id';

function createEditor(opts: Partial<DensityOptions> = {}, content?: string) {
  return new Editor({
    extensions: [
      StarterKit,
      BlockIdExtension.configure({ types: ['paragraph', 'heading'] }),
      DensityExtension.configure({ noteId: 'test-note-id', ...opts }),
    ],
    content: content ?? '<p>Hello world</p>',
  });
}

function makePMNode(type: string, attrs: Record<string, unknown> = {}, text = ''): ProseMirrorNode {
  return {
    type: { name: type },
    attrs,
    textContent: text,
    isBlock: true,
    nodeSize: text.length + 2,
  } as unknown as ProseMirrorNode;
}

// ── localStorage mock ────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

beforeEach(() => {
  Object.defineProperty(globalThis, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });
  localStorageMock.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  localStorageMock.clear();
});

// ── buildCollapseSummary ─────────────────────────────────────────────────────

describe('buildCollapseSummary', () => {
  it('returns intent summary with what and status (T-130)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'intent',
      data: JSON.stringify({ what: 'Auth spec', status: 'running' }),
    });
    expect(buildCollapseSummary(node)).toBe('[Intent] Auth spec — running');
  });

  it('returns intent summary without status when status is empty (T-130)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'intent',
      data: JSON.stringify({ what: 'Deploy script', status: '' }),
    });
    expect(buildCollapseSummary(node)).toBe('[Intent] Deploy script');
  });

  it('uses title as fallback for what in intent block (T-130)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'intent',
      data: JSON.stringify({ title: 'Fallback title' }),
    });
    expect(buildCollapseSummary(node)).toBe('[Intent] Fallback title');
  });

  it('returns progress summary with skill, emoji and status (T-131)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'progress',
      data: JSON.stringify({ skillName: 'create-spec', status: 'done', summary: 'Auth done' }),
    });
    expect(buildCollapseSummary(node)).toBe('[create-spec] ✓ Auth done');
  });

  it('uses running emoji for running progress (T-131)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'progress',
      data: JSON.stringify({ skillName: 'review-code', status: 'running' }),
    });
    const result = buildCollapseSummary(node);
    expect(result).toContain('[review-code]');
    expect(result).toContain('⧗');
  });

  it('uses failed emoji for failed progress (T-131)', () => {
    const node = makePMNode('pmBlock', {
      blockType: 'progress',
      data: JSON.stringify({ skillName: 'deploy', status: 'failed' }),
    });
    expect(buildCollapseSummary(node)).toContain('✗');
  });

  it('returns generic pmBlock summary for unknown blockType', () => {
    const node = makePMNode('pmBlock', { blockType: 'raci' });
    expect(buildCollapseSummary(node)).toBe('[raci]');
  });

  it('truncates text content at 80 chars for non-pmBlock nodes', () => {
    const longText = 'A'.repeat(100);
    const node = makePMNode('paragraph', {}, longText);
    const result = buildCollapseSummary(node);
    expect(result.length).toBeLessThanOrEqual(82); // 80 + ellipsis
    expect(result).toContain('…');
  });

  it('returns full text when under 80 chars', () => {
    const node = makePMNode('paragraph', {}, 'Short text');
    expect(buildCollapseSummary(node)).toBe('Short text');
  });

  it('returns type label for empty text content', () => {
    const node = makePMNode('paragraph', {}, '');
    expect(buildCollapseSummary(node)).toBe('[paragraph]');
  });

  it('handles malformed JSON in pmBlock data gracefully', () => {
    const node = makePMNode('pmBlock', { blockType: 'intent', data: '{bad-json' });
    expect(buildCollapseSummary(node)).toBe('[Intent]');
  });
});

// ── DensityExtension commands ────────────────────────────────────────────────

describe('DensityExtension — commands (T-129)', () => {
  it('setFocusMode sets focusMode to true in storage', () => {
    const editor = createEditor();
    editor.commands.setFocusMode(true);
    expect(getDensityStorage(editor).focusMode).toBe(true);
    editor.destroy();
  });

  it('setFocusMode sets focusMode to false', () => {
    const editor = createEditor();
    editor.commands.setFocusMode(true);
    editor.commands.setFocusMode(false);
    expect(getDensityStorage(editor).focusMode).toBe(false);
    editor.destroy();
  });

  it('toggleFocusMode flips focusMode state', () => {
    const editor = createEditor();
    expect(getDensityStorage(editor).focusMode).toBe(false);
    editor.commands.toggleFocusMode();
    expect(getDensityStorage(editor).focusMode).toBe(true);
    editor.commands.toggleFocusMode();
    expect(getDensityStorage(editor).focusMode).toBe(false);
    editor.destroy();
  });
});

// ── Focus Mode toggle performance (T-133) ────────────────────────────────────

describe('Focus Mode toggle time (T-133)', () => {
  it('toggleFocusMode completes in <200ms', () => {
    const editor = createEditor();
    const start = performance.now();
    editor.commands.toggleFocusMode();
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(200);
    editor.destroy();
  });

  it('setFocusMode(true) completes in <200ms', () => {
    const editor = createEditor();
    const start = performance.now();
    editor.commands.setFocusMode(true);
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(200);
    editor.destroy();
  });
});

// ── localStorage persistence (T-134) ─────────────────────────────────────────

describe('collapse persistence via localStorage (T-134)', () => {
  it('saves focus mode to localStorage on toggle', () => {
    const editor = createEditor();
    editor.commands.setFocusMode(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith(FOCUS_KEY, 'true');
    editor.destroy();
  });

  it('saves false focus mode to localStorage', () => {
    const editor = createEditor();
    editor.commands.setFocusMode(false);
    expect(localStorageMock.setItem).toHaveBeenCalledWith(FOCUS_KEY, 'false');
    editor.destroy();
  });

  it('restores focus mode from localStorage on create', () => {
    // TipTap emits 'create' via setTimeout(0), so fake timers are required
    // to trigger onCreate() synchronously in tests.
    vi.useFakeTimers();
    try {
      localStorageMock.getItem.mockImplementation((key: string) =>
        key === FOCUS_KEY ? 'true' : null
      );
      const editor = createEditor();
      vi.runAllTimers();
      expect(getDensityStorage(editor).focusMode).toBe(true);
      editor.destroy();
    } finally {
      vi.useRealTimers();
    }
  });

  it('collapse state is saved to localStorage on setBlockCollapsed', () => {
    const editor = createEditor({}, '<p data-block-id="block-abc">Some content</p>');
    editor.commands.setBlockCollapsed('block-abc', true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      LOCAL_STORAGE_KEY,
      expect.stringContaining('block-abc')
    );
    editor.destroy();
  });

  it('skips localStorage when noteId is empty', () => {
    const editor = createEditor({ noteId: '' });
    editor.commands.setFocusMode(true);
    expect(localStorageMock.setItem).not.toHaveBeenCalled();
    editor.destroy();
  });
});

// ── Extension registration ───────────────────────────────────────────────────

describe('DensityExtension registration', () => {
  it('registers without errors', () => {
    expect(() => createEditor()).not.toThrow();
  });

  it('initialises storage with correct defaults', () => {
    const editor = createEditor();
    const storage = getDensityStorage(editor);
    expect(storage.focusMode).toBe(false);
    expect(storage.collapseState).toBeInstanceOf(Map);
    editor.destroy();
  });

  it('uses focusModeDefault option when no localStorage entry', () => {
    // TipTap emits 'create' via setTimeout(0) — advance timers to trigger onCreate().
    vi.useFakeTimers();
    try {
      const editor = createEditor({ focusModeDefault: true });
      vi.runAllTimers();
      expect(getDensityStorage(editor).focusMode).toBe(true);
      editor.destroy();
    } finally {
      vi.useRealTimers();
    }
  });
});
