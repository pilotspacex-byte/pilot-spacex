import { describe, it, expect, afterEach } from 'vitest';
import { isTauri } from '../tauri';

describe('isTauri', () => {
  afterEach(() => {
    // Clean up any __TAURI_INTERNALS__ we added
    if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
    }
  });

  it('returns false in standard browser context (no __TAURI_INTERNALS__)', () => {
    expect(isTauri()).toBe(false);
  });

  it('returns true when __TAURI_INTERNALS__ is present on window', () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    expect(isTauri()).toBe(true);
  });
});
