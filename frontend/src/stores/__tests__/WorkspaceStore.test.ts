import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WorkspaceStore } from '../WorkspaceStore';
import type { Workspace } from '@/types';

const wsA: Workspace = {
  id: 'ws-a',
  name: 'Alpha',
  slug: 'alpha',
  memberCount: 2,
  memberIds: [],
  ownerId: 'u1',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const wsB: Workspace = {
  id: 'ws-b',
  name: 'Beta',
  slug: 'beta',
  memberCount: 1,
  memberIds: [],
  ownerId: 'u1',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

function createMockApi(items: Workspace[] = [wsA, wsB]) {
  return {
    list: vi.fn().mockResolvedValue({ items }),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    getMembers: vi.fn().mockResolvedValue([]),
    inviteMember: vi.fn(),
    removeMember: vi.fn(),
    updateMemberRole: vi.fn(),
    getFeatureToggles: vi.fn().mockResolvedValue({
      notes: true, issues: false, projects: false, members: true,
      docs: false, skills: true, costs: false, approvals: false,
    }),
    updateFeatureToggles: vi.fn().mockResolvedValue({
      notes: true, issues: false, projects: false, members: true,
      docs: false, skills: true, costs: false, approvals: false,
    }),
  };
}

describe('WorkspaceStore.fetchWorkspaces', () => {
  let store: WorkspaceStore;
  let api: ReturnType<typeof createMockApi>;

  beforeEach(() => {
    store = new WorkspaceStore();
    api = createMockApi();
    store.setApi(api);
  });

  it('populates workspace list without auto-selecting by default', async () => {
    store.selectWorkspace(null);

    await store.fetchWorkspaces();

    expect(store.workspaceList).toHaveLength(2);
    // Should NOT auto-select when ensureSelection is not set
    expect(store.currentWorkspaceId).toBeNull();
  });

  it('auto-selects first workspace when ensureSelection is true and no current', async () => {
    store.selectWorkspace(null);

    await store.fetchWorkspaces({ ensureSelection: true });

    expect(store.workspaceList).toHaveLength(2);
    expect(store.currentWorkspaceId).toBe('ws-a');
  });

  it('auto-selects first workspace when ensureSelection is true and current is stale', async () => {
    store.selectWorkspace('ws-deleted');

    await store.fetchWorkspaces({ ensureSelection: true });

    // currentWorkspaceId was stale (not in fetched list), should reset
    expect(store.currentWorkspaceId).toBe('ws-a');
  });

  it('does not change selection when ensureSelection is false and current is stale', async () => {
    store.selectWorkspace('ws-deleted');

    await store.fetchWorkspaces();

    // Should keep the stale ID — no silent mutation
    expect(store.currentWorkspaceId).toBe('ws-deleted');
  });

  it('keeps current selection when it exists in fetched list', async () => {
    store.selectWorkspace('ws-b');

    await store.fetchWorkspaces({ ensureSelection: true });

    expect(store.currentWorkspaceId).toBe('ws-b');
  });

  it('sets error when api is not initialized', async () => {
    const noApiStore = new WorkspaceStore();

    await noApiStore.fetchWorkspaces();

    expect(noApiStore.error).toBe('Workspace API not initialized');
  });

  it('sets error on api failure', async () => {
    api.list.mockRejectedValue(new Error('Network error'));

    await store.fetchWorkspaces();

    expect(store.error).toBe('Network error');
    expect(store.isLoading).toBe(false);
  });
});
