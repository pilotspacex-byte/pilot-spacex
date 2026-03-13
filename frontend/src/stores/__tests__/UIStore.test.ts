/**
 * Unit tests for UIStore — expandedNodes tree state management.
 *
 * Tests cover toggle, isExpanded, MobX reactivity, localStorage persistence,
 * and hydration of expandedNodes Set.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { autorun } from 'mobx';
import { UIStore } from '../UIStore';

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------

const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: vi.fn((key: string): string | null => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

vi.stubGlobal('localStorage', localStorageMock);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('UIStore — expandedNodes', () => {
  let uiStore: UIStore;

  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    uiStore = new UIStore();
  });

  afterEach(() => {
    uiStore.dispose();
  });

  it('toggleNodeExpanded adds nodeId to expandedNodes set', () => {
    uiStore.toggleNodeExpanded('node-1');

    expect(uiStore.expandedNodes.has('node-1')).toBe(true);
  });

  it('toggleNodeExpanded removes nodeId from expandedNodes if already present', () => {
    uiStore.toggleNodeExpanded('node-1');
    expect(uiStore.expandedNodes.has('node-1')).toBe(true);

    uiStore.toggleNodeExpanded('node-1');
    expect(uiStore.expandedNodes.has('node-1')).toBe(false);
  });

  it('isNodeExpanded returns true for added nodeId, false for absent nodeId', () => {
    expect(uiStore.isNodeExpanded('node-1')).toBe(false);

    uiStore.toggleNodeExpanded('node-1');
    expect(uiStore.isNodeExpanded('node-1')).toBe(true);

    expect(uiStore.isNodeExpanded('node-2')).toBe(false);
  });

  it('MobX reaction serializes expandedNodes to localStorage as string[] array', () => {
    uiStore.toggleNodeExpanded('node-a');
    uiStore.toggleNodeExpanded('node-b');

    // Reaction fires asynchronously — check that setItem was called with the updated state
    const calls = localStorageMock.setItem.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall).toBeDefined();

    const storedValue = JSON.parse(lastCall![1]) as Record<string, unknown>;
    expect(Array.isArray(storedValue.expandedNodes)).toBe(true);
    const expandedNodes = storedValue.expandedNodes as string[];
    expect(expandedNodes).toContain('node-a');
    expect(expandedNodes).toContain('node-b');
  });

  it('hydrate() restores expandedNodes Set from persisted localStorage state', () => {
    // Pre-populate localStorage with a persisted state
    const persistedState = {
      sidebarCollapsed: false,
      sidebarWidth: 260,
      marginPanelWidth: 200,
      theme: 'system',
      expandedNodes: ['persisted-node-1', 'persisted-node-2'],
    };
    localStorageMock.getItem.mockReturnValue(JSON.stringify(persistedState));

    const freshStore = new UIStore();
    freshStore.hydrate();

    expect(freshStore.expandedNodes.has('persisted-node-1')).toBe(true);
    expect(freshStore.expandedNodes.has('persisted-node-2')).toBe(true);
    expect(freshStore.expandedNodes.size).toBe(2);

    freshStore.dispose();
  });

  it('expandedNodes is MobX-observable (Set mutations trigger reactions)', () => {
    let reactionCount = 0;

    // autorun should fire once on setup, then again on each observable change
    const dispose = autorun(() => {
      // Accessing expandedNodes.size makes MobX track mutations on the Set
      const _size = uiStore.expandedNodes.size;
      void _size;
      reactionCount++;
    });

    const initialCount = reactionCount;

    // Trigger mutation — should fire reaction again
    uiStore.toggleNodeExpanded('observable-test-node');

    expect(reactionCount).toBeGreaterThan(initialCount);

    dispose();
  });
});
