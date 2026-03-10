import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { saveLastWorkspacePath, getLastWorkspacePath } from '../workspace-nav';

describe('workspace-nav', () => {
  beforeEach(() => {
    localStorage.clear();
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
});
