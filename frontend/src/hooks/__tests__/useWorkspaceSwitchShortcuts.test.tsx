/**
 * Unit tests for useWorkspaceSwitchShortcuts.
 *
 * Covers ⌘2/⌘3 binding, editor-focus guard, recents-out-of-range no-op,
 * unrelated keys ignored, and listener cleanup on unmount.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import type { Workspace } from '@/types';

// ---------------------------------------------------------------------------
// Mocks (must be hoisted)
// ---------------------------------------------------------------------------

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}));

const workspaceStore = {
  workspaces: new Map<string, Workspace>([
    ['id-a', { id: 'id-a', slug: 'alpha' } as Workspace],
    ['id-b', { id: 'id-b', slug: 'beta' } as Workspace],
    ['id-c', { id: 'id-c', slug: 'gamma' } as Workspace],
  ]),
};

vi.mock('@/stores', () => ({
  useWorkspaceStore: () => workspaceStore,
}));

const getOrderedRecentWorkspacesMock = vi.fn();
const getLastWorkspacePathMock = vi.fn<(slug: string) => string | null>((slug) => '/' + slug);

vi.mock('@/lib/workspace-nav', () => ({
  getOrderedRecentWorkspaces: (store: typeof workspaceStore) =>
    getOrderedRecentWorkspacesMock(store),
  getLastWorkspacePath: (slug: string) => getLastWorkspacePathMock(slug),
}));

// Import AFTER mocks so the module picks up the mocked deps.
import { useWorkspaceSwitchShortcuts } from '../useWorkspaceSwitchShortcuts';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function dispatchKey(key: string, opts: { meta?: boolean; ctrl?: boolean } = {}): void {
  const event = new KeyboardEvent('keydown', {
    key,
    metaKey: opts.meta ?? true, // default mac-style for tests
    ctrlKey: opts.ctrl ?? false,
    bubbles: true,
    cancelable: true,
  });
  act(() => {
    window.dispatchEvent(event);
  });
}

function clearBody(): void {
  while (document.body.firstChild) {
    document.body.removeChild(document.body.firstChild);
  }
}

const ALPHA = { id: 'id-a', slug: 'alpha' } as Workspace;
const BETA = { id: 'id-b', slug: 'beta' } as Workspace;
const GAMMA = { id: 'id-c', slug: 'gamma' } as Workspace;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWorkspaceSwitchShortcuts', () => {
  beforeEach(() => {
    pushMock.mockClear();
    getOrderedRecentWorkspacesMock.mockReset();
    getLastWorkspacePathMock.mockClear();
    getLastWorkspacePathMock.mockImplementation((slug: string) => '/' + slug);
    // Force mac platform for predictable metaKey detection in tests.
    Object.defineProperty(navigator, 'platform', {
      value: 'MacIntel',
      configurable: true,
    });
  });

  afterEach(() => {
    clearBody();
    vi.restoreAllMocks();
  });

  it('⌘2 with recents=[alpha,beta,gamma] navigates to /beta (index 1)', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('2', { meta: true });

    expect(pushMock).toHaveBeenCalledTimes(1);
    expect(pushMock).toHaveBeenCalledWith('/beta');
  });

  it('⌘3 with recents=[alpha,beta,gamma] navigates to /gamma (index 2)', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('3', { meta: true });

    expect(pushMock).toHaveBeenCalledTimes(1);
    expect(pushMock).toHaveBeenCalledWith('/gamma');
  });

  it('⌘1 (and other keys) are ignored — push not called', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('1', { meta: true });
    dispatchKey('4', { meta: true });
    dispatchKey('k', { meta: true });

    expect(pushMock).not.toHaveBeenCalled();
  });

  it('editor-focused (.ProseMirror) bails — push not called', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    // Build a DOM where activeElement is inside a .ProseMirror element.
    const editor = document.createElement('div');
    editor.className = 'ProseMirror';
    const inner = document.createElement('div');
    inner.tabIndex = 0;
    editor.appendChild(inner);
    document.body.appendChild(editor);
    inner.focus();

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('2', { meta: true });

    expect(pushMock).not.toHaveBeenCalled();
  });

  it('input-focused bails — push not called', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('2', { meta: true });

    expect(pushMock).not.toHaveBeenCalled();
  });

  it('out-of-range (recents=[solo], ⌘2 pressed) does not throw and does not push', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA]);

    renderHook(() => useWorkspaceSwitchShortcuts());

    expect(() => dispatchKey('2', { meta: true })).not.toThrow();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it('falls back to /${slug} when getLastWorkspacePath returns null (Rule 1 — bug fix)', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);
    getLastWorkspacePathMock.mockReturnValueOnce(null);

    renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('2', { meta: true });

    expect(pushMock).toHaveBeenCalledWith('/beta');
  });

  it('cleanup: unmount removes listener — subsequent keypress does not push', () => {
    getOrderedRecentWorkspacesMock.mockReturnValue([ALPHA, BETA, GAMMA]);

    const { unmount } = renderHook(() => useWorkspaceSwitchShortcuts());

    dispatchKey('2', { meta: true });
    expect(pushMock).toHaveBeenCalledTimes(1);

    unmount();
    pushMock.mockClear();

    dispatchKey('2', { meta: true });
    expect(pushMock).not.toHaveBeenCalled();
  });
});
