/**
 * Unit tests for useSwitcherQueryStringSync.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { act } from 'react';
import { UIStore } from '@/stores/UIStore';

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

import { useSwitcherQueryStringSync } from '../useSwitcherQueryStringSync';

function setUrl(search: string): void {
  currentSearch = search;
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search, pathname: '/workspace' },
    writable: true,
    configurable: true,
  });
}

describe('useSwitcherQueryStringSync', () => {
  beforeEach(() => {
    replaceMock.mockClear();
    uiStore = new UIStore();
    setUrl('');
  });

  it('hydrates workspaceSwitcherOpen from ?switcher=1 on mount', () => {
    setUrl('?switcher=1');
    expect(uiStore.workspaceSwitcherOpen).toBe(false);

    renderHook(() => useSwitcherQueryStringSync());

    expect(uiStore.workspaceSwitcherOpen).toBe(true);
  });

  it('programmatic openWorkspaceSwitcher() → router.replace called with switcher=1', async () => {
    renderHook(() => useSwitcherQueryStringSync());
    replaceMock.mockClear();

    act(() => uiStore.openWorkspaceSwitcher());

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[0]![0] as string;
    expect(url).toContain('switcher=1');
    expect(replaceMock.mock.calls[0]![1]).toEqual({ scroll: false });
  });

  it('closeWorkspaceSwitcher() → switcher param stripped from URL', async () => {
    setUrl('?switcher=1');
    renderHook(() => useSwitcherQueryStringSync());
    expect(uiStore.workspaceSwitcherOpen).toBe(true);
    replaceMock.mockClear();

    act(() => uiStore.closeWorkspaceSwitcher());

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[0]![0] as string;
    expect(url).not.toContain('switcher=');
  });

  it('preserves unrelated query params when toggling switcher', async () => {
    setUrl('?peek=abc&peekType=task');
    renderHook(() => useSwitcherQueryStringSync());

    act(() => uiStore.openWorkspaceSwitcher());

    await waitFor(() => expect(replaceMock).toHaveBeenCalled());
    const url = replaceMock.mock.calls[0]![0] as string;
    expect(url).toContain('peek=abc');
    expect(url).toContain('peekType=task');
    expect(url).toContain('switcher=1');
  });
});
