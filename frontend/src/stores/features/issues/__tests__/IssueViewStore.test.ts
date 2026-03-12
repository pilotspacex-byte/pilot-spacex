import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { IssueViewStore } from '../IssueViewStore';

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock, writable: true });
Object.defineProperty(global, 'window', { value: global, writable: true });

describe('IssueViewStore', () => {
  let store: IssueViewStore;

  beforeEach(() => {
    localStorageMock.clear();
    store = new IssueViewStore();
  });

  afterEach(() => {
    store.dispose();
  });

  describe('ViewMode type includes priority', () => {
    it('setViewMode accepts board, list, table', () => {
      store.setViewMode('board');
      expect(store.viewMode).toBe('board');
      store.setViewMode('list');
      expect(store.viewMode).toBe('list');
      store.setViewMode('table');
      expect(store.viewMode).toBe('table');
    });
  });

  describe('getEffectiveViewMode', () => {
    it('returns global viewMode when no projectId provided', () => {
      store.setViewMode('list');
      expect(store.getEffectiveViewMode()).toBe('list');
    });

    it('returns global viewMode when projectId is provided but no project-specific mode is set', () => {
      store.setViewMode('board');
      expect(store.getEffectiveViewMode('proj-1')).toBe('board');
    });

    it('returns project-specific mode when set', () => {
      store.setViewMode('board');
      store.setEffectiveViewMode('priority', 'proj-1');
      expect(store.getEffectiveViewMode('proj-1')).toBe('priority');
    });

    it('returns global viewMode for a different project without specific mode', () => {
      store.setViewMode('table');
      store.setEffectiveViewMode('priority', 'proj-1');
      expect(store.getEffectiveViewMode('proj-2')).toBe('table');
    });
  });

  describe('setEffectiveViewMode', () => {
    it('updates global viewMode when projectId is not provided', () => {
      store.setEffectiveViewMode('list');
      expect(store.viewMode).toBe('list');
      expect(store.getEffectiveViewMode()).toBe('list');
    });

    it('stores project-specific mode without affecting global viewMode', () => {
      store.setViewMode('board');
      store.setEffectiveViewMode('priority', 'proj-1');
      expect(store.viewMode).toBe('board');
      expect(store.projectViewModes.get('proj-1')).toBe('priority');
    });

    it('overwrites existing project-specific mode', () => {
      store.setEffectiveViewMode('priority', 'proj-1');
      store.setEffectiveViewMode('table', 'proj-1');
      expect(store.getEffectiveViewMode('proj-1')).toBe('table');
    });

    it('accepts priority as a valid ViewMode', () => {
      store.setEffectiveViewMode('priority', 'proj-1');
      expect(store.getEffectiveViewMode('proj-1')).toBe('priority');
    });

    it('accepts priority as global viewMode', () => {
      store.setEffectiveViewMode('priority');
      expect(store.viewMode).toBe('priority');
    });
  });

  describe('projectViewModes persistence', () => {
    it('persists projectViewModes to localStorage', async () => {
      store.setEffectiveViewMode('priority', 'proj-1');
      store.setEffectiveViewMode('table', 'proj-2');

      // Wait for MobX reaction to fire
      await new Promise((r) => setTimeout(r, 10));

      const stored = JSON.parse(localStorageMock.getItem('pilot-space:issue-view-state') ?? '{}');
      expect(stored.projectViewModes).toEqual({ 'proj-1': 'priority', 'proj-2': 'table' });
    });

    it('restores projectViewModes from localStorage on hydrate', async () => {
      // Pre-seed localStorage
      localStorageMock.setItem(
        'pilot-space:issue-view-state',
        JSON.stringify({
          viewMode: 'list',
          cardDensity: 'comfortable',
          collapsedColumns: [],
          collapsedGroups: [],
          columnWidths: {},
          hiddenColumns: [],
          wipLimits: {},
          filterStates: [],
          filterPriorities: [],
          filterTypes: [],
          filterAssigneeIds: [],
          filterLabelIds: [],
          filterProjectIds: [],
          projectViewModes: { 'proj-1': 'priority', 'proj-2': 'table' },
        })
      );

      const freshStore = new IssueViewStore();
      freshStore.hydrate();

      expect(freshStore.getEffectiveViewMode('proj-1')).toBe('priority');
      expect(freshStore.getEffectiveViewMode('proj-2')).toBe('table');
      freshStore.dispose();
    });

    it('handles missing projectViewModes in stored state gracefully', () => {
      localStorageMock.setItem(
        'pilot-space:issue-view-state',
        JSON.stringify({
          viewMode: 'list',
          cardDensity: 'comfortable',
          collapsedColumns: [],
          collapsedGroups: [],
          columnWidths: {},
          hiddenColumns: [],
          wipLimits: {},
          filterStates: [],
          filterPriorities: [],
          filterTypes: [],
          filterAssigneeIds: [],
          filterLabelIds: [],
          filterProjectIds: [],
          // no projectViewModes
        })
      );

      const freshStore = new IssueViewStore();
      freshStore.hydrate();
      expect(freshStore.getEffectiveViewMode('proj-1')).toBe('list');
      freshStore.dispose();
    });
  });

  describe('reset', () => {
    it('clears projectViewModes on reset', () => {
      store.setEffectiveViewMode('priority', 'proj-1');
      store.reset();
      expect(store.projectViewModes.size).toBe(0);
      expect(store.getEffectiveViewMode('proj-1')).toBe('board');
    });
  });
});
