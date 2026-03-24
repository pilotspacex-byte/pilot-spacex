import { describe, it, expect, beforeEach } from 'vitest';
import { GitWebStore } from './GitWebStore';
import type { ChangedFile, GitRepo } from '@/features/source-control/types';

function makeSampleFiles(): Omit<ChangedFile, 'staged'>[] {
  return [
    { path: 'src/index.ts', status: 'modified', additions: 10, deletions: 2, patch: null },
    { path: 'src/utils.ts', status: 'added', additions: 30, deletions: 0, patch: null },
    { path: 'src/old.ts', status: 'deleted', additions: 0, deletions: 15, patch: null },
  ];
}

function makeSampleRepo(): GitRepo {
  return {
    owner: 'acme',
    repo: 'app',
    provider: 'github',
    integrationId: 'int-1',
    defaultBranch: 'main',
  };
}

describe('GitWebStore', () => {
  let store: GitWebStore;

  beforeEach(() => {
    store = new GitWebStore();
  });

  it('has empty initial state', () => {
    expect(store.currentRepo).toBeNull();
    expect(store.currentBranch).toBe('');
    expect(store.defaultBranch).toBe('');
    expect(store.changedFiles).toEqual([]);
    expect(store.commitMessage).toBe('');
    expect(store.selectedFilePath).toBeNull();
    expect(store.isLoading).toBe(false);
    expect(store.isCommitting).toBe(false);
    expect(store.error).toBeNull();
  });

  it('setChangedFiles maps API response with staged=false', () => {
    store.setChangedFiles(makeSampleFiles());
    expect(store.changedFiles).toHaveLength(3);
    expect(store.changedFiles.every((f) => f.staged === false)).toBe(true);
    expect(store.changedFiles[0]?.path).toBe('src/index.ts');
  });

  it('stageFile sets staged=true on matching file', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageFile('src/index.ts');

    const staged = store.changedFiles.find((f) => f.path === 'src/index.ts');
    expect(staged?.staged).toBe(true);

    // Others remain unstaged
    const unstaged = store.changedFiles.find((f) => f.path === 'src/utils.ts');
    expect(unstaged?.staged).toBe(false);
  });

  it('unstageFile sets staged=false on matching file', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageFile('src/index.ts');
    store.unstageFile('src/index.ts');

    const file = store.changedFiles.find((f) => f.path === 'src/index.ts');
    expect(file?.staged).toBe(false);
  });

  it('stageAll sets staged=true on all files', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();

    expect(store.changedFiles.every((f) => f.staged)).toBe(true);
  });

  it('unstageAll sets staged=false on all files', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.unstageAll();

    expect(store.changedFiles.every((f) => !f.staged)).toBe(true);
  });

  it('stagedFiles returns only staged files', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageFile('src/index.ts');
    store.stageFile('src/old.ts');

    expect(store.stagedFiles).toHaveLength(2);
    expect(store.stagedFiles.map((f) => f.path)).toEqual(['src/index.ts', 'src/old.ts']);
  });

  it('unstagedFiles returns only unstaged files', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageFile('src/index.ts');

    expect(store.unstagedFiles).toHaveLength(2);
    expect(store.unstagedFiles.map((f) => f.path)).toEqual(['src/utils.ts', 'src/old.ts']);
  });

  it('switchBranch clears files, message, and selection', () => {
    store.setChangedFiles(makeSampleFiles());
    store.setCommitMessage('wip');
    store.selectFile('src/index.ts');

    store.switchBranch('feature/x');

    expect(store.currentBranch).toBe('feature/x');
    expect(store.changedFiles).toEqual([]);
    expect(store.commitMessage).toBe('');
    expect(store.selectedFilePath).toBeNull();
  });

  it('canCommit returns false with no staged files', () => {
    store.setChangedFiles(makeSampleFiles());
    store.setCommitMessage('some message');

    expect(store.canCommit).toBe(false);
  });

  it('canCommit returns false with empty message', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('');

    expect(store.canCommit).toBe(false);
  });

  it('canCommit returns false with whitespace-only message', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('   ');

    expect(store.canCommit).toBe(false);
  });

  it('canCommit returns true with staged files and non-empty message', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('feat: add stuff');

    expect(store.canCommit).toBe(true);
  });

  it('canCommit returns false while committing', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('feat: add stuff');
    store.isCommitting = true;

    expect(store.canCommit).toBe(false);
  });

  it('clearAfterCommit resets message and staged flags', () => {
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('feat: done');

    store.clearAfterCommit();

    expect(store.commitMessage).toBe('');
    expect(store.changedFiles.every((f) => !f.staged)).toBe(true);
    // Files themselves are still present
    expect(store.changedFiles).toHaveLength(3);
  });

  it('setRepo sets repo and branch context', () => {
    store.setRepo(makeSampleRepo());

    expect(store.currentRepo?.owner).toBe('acme');
    expect(store.currentBranch).toBe('main');
    expect(store.defaultBranch).toBe('main');
  });

  it('reset clears all state', () => {
    store.setRepo(makeSampleRepo());
    store.setChangedFiles(makeSampleFiles());
    store.stageAll();
    store.setCommitMessage('msg');
    store.selectFile('src/index.ts');
    store.isLoading = true;
    store.error = 'oops';

    store.reset();

    expect(store.currentRepo).toBeNull();
    expect(store.currentBranch).toBe('');
    expect(store.changedFiles).toEqual([]);
    expect(store.commitMessage).toBe('');
    expect(store.selectedFilePath).toBeNull();
    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
  });

  it('changedFileCount returns total count', () => {
    store.setChangedFiles(makeSampleFiles());
    expect(store.changedFileCount).toBe(3);
  });

  it('selectFile updates selectedFilePath', () => {
    store.selectFile('src/foo.ts');
    expect(store.selectedFilePath).toBe('src/foo.ts');

    store.selectFile(null);
    expect(store.selectedFilePath).toBeNull();
  });
});
