import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  saveLastWorkspacePath,
  getLastWorkspacePath,
  getOrderedRecentWorkspaces,
} from '../workspace-nav';
import type { Workspace } from '@/types';

vi.mock('@/components/workspace-selector', () => ({
  getRecentWorkspaces: vi.fn(),
}));

import { getRecentWorkspaces } from '@/components/workspace-selector';

describe('workspace-nav', () => {
  beforeEach(() => {
    // jsdom in this project ships without localStorage.clear — guard for compat.
    if (typeof localStorage !== 'undefined' && typeof localStorage.clear === 'function') {
      localStorage.clear();
    } else if (typeof localStorage !== 'undefined') {
      // Best-effort manual clear when .clear is unavailable.
      const len = (localStorage as Storage).length ?? 0;
      const keys: string[] = [];
      for (let i = 0; i < len; i += 1) {
        const k = (localStorage as Storage).key?.(i);
        if (k) keys.push(k);
      }
      keys.forEach((k) => (localStorage as Storage).removeItem?.(k));
    }
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('saveLastWorkspacePath', () => {
    it('stores path under correct key', () => {
      saveLastWorkspacePath('my-ws', '/my-ws/issues');
      expect(localStorage.getItem('pilot-space:last-path:my-ws')).toBe('/my-ws/issues');
    });

    it('does NOT store settings paths', () => {
      saveLastWorkspacePath('my-ws', '/my-ws/settings/members');
      expect(localStorage.getItem('pilot-space:last-path:my-ws')).toBeNull();
    });

    it('does NOT overwrite a previously stored value when called with a settings path', () => {
      saveLastWorkspacePath('my-ws', '/my-ws/issues');
      saveLastWorkspacePath('my-ws', '/my-ws/settings/members');
      expect(localStorage.getItem('pilot-space:last-path:my-ws')).toBe('/my-ws/issues');
    });

    it('is a no-op in SSR (window undefined)', () => {
      const originalWindow = globalThis.window;
      // @ts-expect-error — intentionally deleting window to simulate SSR
      delete globalThis.window;
      expect(() => saveLastWorkspacePath('my-ws', '/my-ws/issues')).not.toThrow();
      globalThis.window = originalWindow;
    });

    it('swallows localStorage errors silently', () => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new DOMException('QuotaExceededError');
      });
      expect(() => saveLastWorkspacePath('my-ws', '/my-ws/issues')).not.toThrow();
    });
  });

  describe('getLastWorkspacePath', () => {
    it('returns stored path', () => {
      localStorage.setItem('pilot-space:last-path:my-ws', '/my-ws/issues');
      expect(getLastWorkspacePath('my-ws')).toBe('/my-ws/issues');
    });

    it('returns null when not set', () => {
      expect(getLastWorkspacePath('my-ws')).toBeNull();
    });

    it('returns null on localStorage error', () => {
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new DOMException('SecurityError');
      });
      expect(getLastWorkspacePath('my-ws')).toBeNull();
    });

    it('returns null in SSR (window undefined)', () => {
      const originalWindow = globalThis.window;
      // @ts-expect-error — intentionally deleting window to simulate SSR
      delete globalThis.window;
      expect(getLastWorkspacePath('my-ws')).toBeNull();
      globalThis.window = originalWindow;
    });
  });

  describe('getOrderedRecentWorkspaces', () => {
    function makeWorkspace(id: string, slug: string): Workspace {
      return { id, slug, name: slug } as Workspace;
    }

    function makeStore(workspaces: Workspace[]): { workspaces: Map<string, Workspace> } {
      const map = new Map<string, Workspace>();
      for (const ws of workspaces) map.set(ws.id, ws);
      return { workspaces: map };
    }

    it('returns workspaces in recency order (recents=[beta,gamma,alpha] → [beta,gamma,alpha])', () => {
      vi.mocked(getRecentWorkspaces).mockReturnValue([
        { slug: 'beta', lastVisited: 3 },
        { slug: 'gamma', lastVisited: 2 },
        { slug: 'alpha', lastVisited: 1 },
      ]);
      const alpha = makeWorkspace('id-a', 'alpha');
      const beta = makeWorkspace('id-b', 'beta');
      const gamma = makeWorkspace('id-c', 'gamma');
      const store = makeStore([alpha, beta, gamma]);

      const result = getOrderedRecentWorkspaces(store);

      expect(result.map((w) => w.slug)).toEqual(['beta', 'gamma', 'alpha']);
    });

    it('filters out slugs whose workspace is not in the Map', () => {
      vi.mocked(getRecentWorkspaces).mockReturnValue([
        { slug: 'ghost', lastVisited: 2 },
        { slug: 'beta', lastVisited: 1 },
      ]);
      const beta = makeWorkspace('id-b', 'beta');
      const store = makeStore([beta]);

      const result = getOrderedRecentWorkspaces(store);

      expect(result).toHaveLength(1);
      expect(result[0]!.slug).toBe('beta');
    });

    it('returns empty array when recents is empty', () => {
      vi.mocked(getRecentWorkspaces).mockReturnValue([]);
      const store = makeStore([makeWorkspace('id-a', 'alpha')]);

      expect(getOrderedRecentWorkspaces(store)).toEqual([]);
    });

    it('preserves recency order even when Map insertion order differs', () => {
      vi.mocked(getRecentWorkspaces).mockReturnValue([
        { slug: 'gamma', lastVisited: 3 },
        { slug: 'alpha', lastVisited: 2 },
        { slug: 'beta', lastVisited: 1 },
      ]);
      // Map insertion order alphabetical (alpha, beta, gamma) — different from recency
      const alpha = makeWorkspace('id-a', 'alpha');
      const beta = makeWorkspace('id-b', 'beta');
      const gamma = makeWorkspace('id-c', 'gamma');
      const store = makeStore([alpha, beta, gamma]);

      const result = getOrderedRecentWorkspaces(store);

      expect(result.map((w) => w.slug)).toEqual(['gamma', 'alpha', 'beta']);
    });
  });
});
