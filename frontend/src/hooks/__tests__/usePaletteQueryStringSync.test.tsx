/**
 * Unit tests for usePaletteQueryStringSync.
 *
 * Covers mount-time hydration from `?palette=1`/`?scope=`, scope whitelist guard,
 * programmatic open/close → URL writes, and scope updates while open.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { act } from 'react';
import { UIStore } from '@/stores/UIStore';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const replaceMock = vi.fn();
let currentSearch = '';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock }),
  usePathname: () => '/workspace',
  useSearchParams: () => new URLSearchParams(currentSearch),
}));

let uiStore: UIStore;

vi.mock('@/stores', () => ({
  useUIStore: () => uiStore,
}));

// Import AFTER mocks
import { usePaletteQueryStringSync } from '../usePaletteQueryStringSync';

function setUrl(search: string): void {
  currentSearch = search;
  // also align window.location.search so the reaction reads consistent state
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search, pathname: '/workspace' },
    writable: true,
    configurable: true,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('usePaletteQueryStringSync', () => {
  beforeEach(() => {
    replaceMock.mockClear();
    uiStore = new UIStore();
    setUrl('');
  });

  it('hydrates uiStore.commandPaletteOpen from ?palette=1 on mount', () => {
    setUrl('?palette=1');
    expect(uiStore.commandPaletteOpen).toBe(false);

    renderHook(() => usePaletteQueryStringSync());

    expect(uiStore.commandPaletteOpen).toBe(true);
  });

  it('hydrates paletteScope from ?palette=1&scope=tasks', () => {
    setUrl('?palette=1&scope=tasks');

    renderHook(() => usePaletteQueryStringSync());

    expect(uiStore.commandPaletteOpen).toBe(true);
    expect(uiStore.paletteScope).toBe('tasks');
  });

  it("ignores invalid scope values (?scope=invalid → paletteScope stays 'all')", () => {
    setUrl('?palette=1&scope=invalid');

    renderHook(() => usePaletteQueryStringSync());

    expect(uiStore.commandPaletteOpen).toBe(true);
    expect(uiStore.paletteScope).toBe('all');
  });

  it('programmatic openCommandPalette() → router.replace called with palette=1', async () => {
    renderHook(() => usePaletteQueryStringSync());
    replaceMock.mockClear();

    act(() => uiStore.openCommandPalette());

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[0]![0] as string;
    expect(url).toContain('palette=1');
    expect(replaceMock.mock.calls[0]![1]).toEqual({ scroll: false });
  });

  it('setPaletteScope(\'chats\') while open → URL contains scope=chats', async () => {
    renderHook(() => usePaletteQueryStringSync());

    act(() => {
      uiStore.openCommandPalette();
    });
    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    replaceMock.mockClear();

    // Update window.location.search to reflect the previous URL write so
    // the next reaction starts from the correct base state.
    setUrl('?palette=1');

    act(() => {
      uiStore.setPaletteScope('chats');
    });

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[replaceMock.mock.calls.length - 1]![0] as string;
    expect(url).toContain('scope=chats');
    expect(url).toContain('palette=1');
  });

  it('closeCommandPalette() → URL has no palette / scope / q', async () => {
    setUrl('?palette=1&scope=tasks&q=hello');

    renderHook(() => usePaletteQueryStringSync());
    expect(uiStore.commandPaletteOpen).toBe(true);

    replaceMock.mockClear();

    act(() => uiStore.closeCommandPalette());

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[0]![0] as string;
    expect(url).not.toContain('palette=');
    expect(url).not.toContain('scope=');
    expect(url).not.toContain('q=');
  });

  it("scope='all' while open → scope param omitted (kept palette=1 only)", async () => {
    renderHook(() => usePaletteQueryStringSync());

    act(() => {
      uiStore.openCommandPalette();
      uiStore.setPaletteScope('topics');
    });
    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    replaceMock.mockClear();
    setUrl('?palette=1&scope=topics');

    act(() => uiStore.setPaletteScope('all'));

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[replaceMock.mock.calls.length - 1]![0] as string;
    expect(url).toContain('palette=1');
    expect(url).not.toContain('scope=');
  });
});
