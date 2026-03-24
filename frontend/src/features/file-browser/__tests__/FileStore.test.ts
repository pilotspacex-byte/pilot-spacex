import { describe, it, expect, beforeEach } from 'vitest';
import { FileStore } from '../stores/FileStore';
import type { OpenFile } from '@/features/editor/types';

function makeFile(overrides: Partial<OpenFile> & { id: string }): Omit<OpenFile, 'isDirty'> {
  return {
    name: `${overrides.id}.ts`,
    path: `/src/${overrides.id}.ts`,
    source: 'local',
    language: 'typescript',
    content: `// ${overrides.id}`,
    isReadOnly: false,
    ...overrides,
  };
}

describe('FileStore', () => {
  let store: FileStore;

  beforeEach(() => {
    store = new FileStore();
  });

  describe('initial state', () => {
    it('starts with no open files', () => {
      expect(store.tabs).toEqual([]);
      expect(store.activeFileId).toBeNull();
      expect(store.activeFile).toBeUndefined();
      expect(store.hasDirtyFiles).toBe(false);
    });
  });

  describe('openFile', () => {
    it('adds file to openFiles and sets activeFileId', () => {
      store.openFile(makeFile({ id: 'f1' }));
      expect(store.tabs).toHaveLength(1);
      expect(store.activeFileId).toBe('f1');
      expect(store.activeFile).toBeDefined();
      expect(store.activeFile!.id).toBe('f1');
      expect(store.activeFile!.isDirty).toBe(false);
    });

    it('does not duplicate when called with same id', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f1' }));
      expect(store.tabs).toHaveLength(1);
    });

    it('sets active to the opened file', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      expect(store.activeFileId).toBe('f2');
    });
  });

  describe('closeFile', () => {
    it('removes file from openFiles', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      store.closeFile('f1');
      expect(store.tabs).toHaveLength(1);
      expect(store.tabs[0]!.id).toBe('f2');
    });

    it('falls back activeFileId to last remaining tab', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      store.closeFile('f2');
      expect(store.activeFileId).toBe('f1');
    });

    it('sets activeFileId to null when closing last tab', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.closeFile('f1');
      expect(store.activeFileId).toBeNull();
      expect(store.activeFile).toBeUndefined();
    });
  });

  describe('tabs computed', () => {
    it('returns array from openFiles values', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      const tabs = store.tabs;
      expect(tabs).toHaveLength(2);
      expect(tabs.map((t) => t.id)).toEqual(['f1', 'f2']);
    });
  });

  describe('markDirty / markClean', () => {
    it('markDirty sets isDirty to true', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.markDirty('f1');
      expect(store.activeFile!.isDirty).toBe(true);
    });

    it('markClean sets isDirty to false', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.markDirty('f1');
      store.markClean('f1');
      expect(store.activeFile!.isDirty).toBe(false);
    });
  });

  describe('hasDirtyFiles', () => {
    it('returns true when any file is dirty', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      store.markDirty('f1');
      expect(store.hasDirtyFiles).toBe(true);
    });

    it('returns false when no files are dirty', () => {
      store.openFile(makeFile({ id: 'f1' }));
      expect(store.hasDirtyFiles).toBe(false);
    });
  });

  describe('closeAll', () => {
    it('clears all tabs and sets activeFileId to null', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      store.closeAll();
      expect(store.tabs).toHaveLength(0);
      expect(store.activeFileId).toBeNull();
    });
  });

  describe('closeOthers', () => {
    it('keeps only the specified file open', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.openFile(makeFile({ id: 'f2' }));
      store.openFile(makeFile({ id: 'f3' }));
      store.closeOthers('f1');
      expect(store.tabs).toHaveLength(1);
      expect(store.tabs[0]!.id).toBe('f1');
      expect(store.activeFileId).toBe('f1');
    });
  });

  describe('MAX_TABS eviction', () => {
    it('evicts oldest non-dirty, non-active tab when at max', () => {
      // Open 12 tabs
      for (let i = 1; i <= 12; i++) {
        store.openFile(makeFile({ id: `f${i}` }));
      }
      expect(store.tabs).toHaveLength(12);

      // Mark f1 as dirty so it should not be evicted
      store.markDirty('f1');
      // f12 is active, so it should not be evicted

      // Open one more tab -- should evict f2 (first non-dirty, non-active)
      store.openFile(makeFile({ id: 'f13' }));
      expect(store.tabs).toHaveLength(12);
      expect(store.tabs.find((t) => t.id === 'f2')).toBeUndefined();
      expect(store.tabs.find((t) => t.id === 'f1')).toBeDefined(); // dirty, kept
      expect(store.tabs.find((t) => t.id === 'f13')).toBeDefined(); // new
    });
  });

  describe('updateContent', () => {
    it('updates content and marks dirty', () => {
      store.openFile(makeFile({ id: 'f1' }));
      store.updateContent('f1', 'new content');
      expect(store.activeFile!.content).toBe('new content');
      expect(store.activeFile!.isDirty).toBe(true);
    });
  });
});
