import { describe, it, expect, beforeEach } from 'vitest';
import { GitStore } from '../GitStore';
import type { ChangedFile } from '../../git-types';

/**
 * Helper: create a ChangedFile with minimal required fields.
 */
function makeFile(path: string, status: ChangedFile['status'] = 'modified'): ChangedFile {
  return {
    path,
    status,
    additions: 1,
    deletions: 0,
    patch: null,
    staged: false,
  };
}

describe('GitStore', () => {
  let store: GitStore;

  beforeEach(() => {
    store = new GitStore();
  });

  // ─── setBranch ────────────────────────────────────────────────────────────

  describe('setBranch', () => {
    it('updates currentBranch', () => {
      store.setBranch('feature/my-feature');
      expect(store.currentBranch).toBe('feature/my-feature');
    });

    it('overwrites the previous branch', () => {
      store.setBranch('main');
      store.setBranch('develop');
      expect(store.currentBranch).toBe('develop');
    });
  });

  // ─── setRepoInfo ─────────────────────────────────────────────────────────

  describe('setRepoInfo', () => {
    it('sets owner and repo', () => {
      store.setRepoInfo('acme', 'my-app');
      expect(store.owner).toBe('acme');
      expect(store.repo).toBe('my-app');
    });

    it('overwrites previous repo info', () => {
      store.setRepoInfo('old-owner', 'old-repo');
      store.setRepoInfo('new-owner', 'new-repo');
      expect(store.owner).toBe('new-owner');
      expect(store.repo).toBe('new-repo');
    });
  });

  // ─── setChangedFiles ──────────────────────────────────────────────────────

  describe('setChangedFiles', () => {
    it('updates changedFiles array', () => {
      const files = [makeFile('src/index.ts'), makeFile('src/utils.ts', 'added')];
      store.setChangedFiles(files);
      expect(store.changedFiles).toHaveLength(2);
      expect(store.changedFiles[0]?.path).toBe('src/index.ts');
    });

    it('replaces previous changedFiles on subsequent calls', () => {
      store.setChangedFiles([makeFile('file-a.ts')]);
      store.setChangedFiles([makeFile('file-b.ts'), makeFile('file-c.ts')]);
      expect(store.changedFiles).toHaveLength(2);
      expect(store.changedFiles[0]?.path).toBe('file-b.ts');
    });
  });

  // ─── hasChanges (computed) ────────────────────────────────────────────────

  describe('hasChanges', () => {
    it('returns false when changedFiles is empty', () => {
      expect(store.hasChanges).toBe(false);
    });

    it('returns true when changedFiles is non-empty', () => {
      store.setChangedFiles([makeFile('src/app.ts')]);
      expect(store.hasChanges).toBe(true);
    });

    it('returns false after changedFiles is cleared', () => {
      store.setChangedFiles([makeFile('src/app.ts')]);
      store.setChangedFiles([]);
      expect(store.hasChanges).toBe(false);
    });
  });

  // ─── repoFullName (computed) ──────────────────────────────────────────────

  describe('repoFullName', () => {
    it('returns null when owner and repo are not set', () => {
      expect(store.repoFullName).toBeNull();
    });

    it('returns "owner/repo" when both are set', () => {
      store.setRepoInfo('acme', 'my-app');
      expect(store.repoFullName).toBe('acme/my-app');
    });

    it('returns null when only owner is set (no repo)', () => {
      store.owner = 'acme';
      expect(store.repoFullName).toBeNull();
    });

    it('returns null when only repo is set (no owner)', () => {
      store.repo = 'my-app';
      expect(store.repoFullName).toBeNull();
    });
  });

  // ─── reset ───────────────────────────────────────────────────────────────

  describe('reset', () => {
    it('clears all state back to defaults', () => {
      store.setBranch('feature/x');
      store.setRepoInfo('owner', 'repo');
      store.setChangedFiles([makeFile('src/index.ts')]);

      store.reset();

      expect(store.currentBranch).toBeNull();
      expect(store.defaultBranch).toBeNull();
      expect(store.owner).toBeNull();
      expect(store.repo).toBeNull();
      expect(store.changedFiles).toHaveLength(0);
      expect(store.isLoading).toBe(false);
    });
  });
});
