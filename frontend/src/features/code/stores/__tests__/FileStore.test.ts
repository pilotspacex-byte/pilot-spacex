import { describe, it, expect, beforeEach } from 'vitest';
import { FileStore } from '../FileStore';
import type { FileTab } from '../../types';

/**
 * Helper: create a FileTab with minimal required fields.
 * lastAccessed defaults to the current time, content to null.
 */
function makeTab(id: string, overrides?: Partial<FileTab>): FileTab {
  return {
    id,
    name: `${id}.ts`,
    path: `/src/${id}.ts`,
    language: 'typescript',
    isDirty: false,
    content: null,
    lastAccessed: Date.now(),
    ...overrides,
  };
}

describe('FileStore', () => {
  let store: FileStore;

  beforeEach(() => {
    store = new FileStore();
  });

  // ─── openFile ──────────────────────────────────────────────────────────────

  describe('openFile', () => {
    it('adds a new file to openFiles and sets it as activeFileId', () => {
      store.openFile(makeTab('f1'));
      expect(store.openFiles.has('f1')).toBe(true);
      expect(store.activeFileId).toBe('f1');
    });

    it('does not duplicate when called with the same id', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f1'));
      expect(store.openFiles.size).toBe(1);
    });

    it('re-activates an already-open file without duplicating it', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.openFile(makeTab('f1')); // re-open f1
      expect(store.openFiles.size).toBe(2);
      expect(store.activeFileId).toBe('f1');
    });
  });

  // ─── LRU eviction at MAX_TABS ──────────────────────────────────────────────

  describe('LRU eviction at MAX_TABS', () => {
    it('evicts the oldest (by lastAccessed) non-dirty tab when at MAX_TABS', () => {
      const now = Date.now();
      // Open 12 files with ascending lastAccessed times
      for (let i = 1; i <= 12; i++) {
        store.openFile(makeTab(`f${i}`, { lastAccessed: now + i }));
      }
      expect(store.openFiles.size).toBe(12);

      // f1 has the lowest lastAccessed — it should be evicted
      store.openFile(makeTab('f13', { lastAccessed: now + 13 }));

      expect(store.openFiles.size).toBe(12);
      expect(store.openFiles.has('f1')).toBe(false); // oldest evicted
      expect(store.openFiles.has('f13')).toBe(true); // new file present
    });

    it('skips dirty files during LRU eviction and evicts next oldest clean file', () => {
      const now = Date.now();
      for (let i = 1; i <= 12; i++) {
        store.openFile(makeTab(`f${i}`, { lastAccessed: now + i }));
      }

      // Mark f1 (oldest) as dirty — should be protected from eviction
      store.markDirty('f1');

      // Open f13 — should evict f2 (second oldest, clean)
      store.openFile(makeTab('f13', { lastAccessed: now + 13 }));

      expect(store.openFiles.size).toBe(12);
      expect(store.openFiles.has('f1')).toBe(true); // dirty — kept
      expect(store.openFiles.has('f2')).toBe(false); // oldest clean — evicted
      expect(store.openFiles.has('f13')).toBe(true); // new file present
    });
  });

  // ─── closeFile ────────────────────────────────────────────────────────────

  describe('closeFile', () => {
    it('removes the file from openFiles', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.closeFile('f1');
      expect(store.openFiles.has('f1')).toBe(false);
      expect(store.openFiles.size).toBe(1);
    });

    it('sets activeFileId to next available tab when closing active file', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.closeFile('f2'); // f2 was active
      expect(store.activeFileId).toBe('f1');
    });

    it('sets activeFileId to null when closing the last tab', () => {
      store.openFile(makeTab('f1'));
      store.closeFile('f1');
      expect(store.activeFileId).toBeNull();
      expect(store.openFiles.size).toBe(0);
    });
  });

  // ─── closeOtherFiles ──────────────────────────────────────────────────────

  describe('closeOtherFiles', () => {
    it('closes all tabs except the given one', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.openFile(makeTab('f3'));
      store.closeOtherFiles('f2');
      expect(store.openFiles.size).toBe(1);
      expect(store.openFiles.has('f2')).toBe(true);
      expect(store.activeFileId).toBe('f2');
    });

    it('skips dirty tabs during closeOtherFiles (keeps them open)', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.openFile(makeTab('f3'));
      store.markDirty('f1'); // f1 is dirty — should be kept

      store.closeOtherFiles('f2');

      // f2 (requested keep) and f1 (dirty) should remain
      expect(store.openFiles.has('f1')).toBe(true); // dirty — kept
      expect(store.openFiles.has('f2')).toBe(true); // explicitly kept
      expect(store.openFiles.has('f3')).toBe(false); // clean other — closed
    });
  });

  // ─── setActiveFile ────────────────────────────────────────────────────────

  describe('setActiveFile', () => {
    it('updates activeFileId', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.setActiveFile('f1');
      expect(store.activeFileId).toBe('f1');
    });

    it('updates lastAccessed timestamp on the target file', () => {
      const before = Date.now();
      store.openFile(makeTab('f1', { lastAccessed: before - 10000 }));
      store.setActiveFile('f1');
      const file = store.openFiles.get('f1')!;
      expect(file.lastAccessed).toBeGreaterThanOrEqual(before);
    });
  });

  // ─── markDirty ───────────────────────────────────────────────────────────

  describe('markDirty', () => {
    it('sets isDirty=true on the specified file', () => {
      store.openFile(makeTab('f1'));
      store.markDirty('f1');
      expect(store.openFiles.get('f1')!.isDirty).toBe(true);
    });

    it('is a no-op for unknown ids', () => {
      expect(() => store.markDirty('nonexistent')).not.toThrow();
    });
  });

  // ─── markClean ───────────────────────────────────────────────────────────

  describe('markClean', () => {
    it('sets isDirty=false on the specified file', () => {
      store.openFile(makeTab('f1'));
      store.markDirty('f1');
      store.markClean('f1');
      expect(store.openFiles.get('f1')!.isDirty).toBe(false);
    });
  });

  // ─── updateContent ───────────────────────────────────────────────────────

  describe('updateContent', () => {
    it('updates content string on the specified file', () => {
      store.openFile(makeTab('f1'));
      store.updateContent('f1', 'hello world');
      expect(store.openFiles.get('f1')!.content).toBe('hello world');
    });

    it('does NOT automatically mark dirty (caller controls dirty state)', () => {
      store.openFile(makeTab('f1'));
      store.updateContent('f1', 'hello world');
      // updateContent itself does not mark dirty — markDirty is separate
      expect(store.openFiles.get('f1')!.isDirty).toBe(false);
    });
  });

  // ─── hasDirtyFiles (computed) ─────────────────────────────────────────────

  describe('hasDirtyFiles', () => {
    it('returns false when no files are open', () => {
      expect(store.hasDirtyFiles).toBe(false);
    });

    it('returns false when all files are clean', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      expect(store.hasDirtyFiles).toBe(false);
    });

    it('returns true when any file is dirty', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.markDirty('f2');
      expect(store.hasDirtyFiles).toBe(true);
    });
  });

  // ─── activeFile (computed) ────────────────────────────────────────────────

  describe('activeFile', () => {
    it('returns null when no file is active', () => {
      expect(store.activeFile).toBeNull();
    });

    it('returns the file matching activeFileId', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.setActiveFile('f1');
      expect(store.activeFile?.id).toBe('f1');
    });

    it('returns null after closing the active file', () => {
      store.openFile(makeTab('f1'));
      store.closeFile('f1');
      expect(store.activeFile).toBeNull();
    });
  });

  // ─── reset ───────────────────────────────────────────────────────────────

  describe('reset', () => {
    it('clears all open files', () => {
      store.openFile(makeTab('f1'));
      store.openFile(makeTab('f2'));
      store.reset();
      expect(store.openFiles.size).toBe(0);
    });

    it('sets activeFileId to null', () => {
      store.openFile(makeTab('f1'));
      store.reset();
      expect(store.activeFileId).toBeNull();
    });
  });
});
