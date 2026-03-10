import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the plugins API module
vi.mock('@/services/api/plugins', () => ({
  pluginsApi: {
    getInstalled: vi.fn(),
    browse: vi.fn(),
    install: vi.fn(),
    uninstall: vi.fn(),
    checkUpdates: vi.fn(),
    saveGitHubPat: vi.fn(),
    getGitHubCredential: vi.fn(),
  },
}));

import { PluginsStore } from '../PluginsStore';
import type { InstalledPlugin, AvailablePlugin } from '../PluginsStore';
import { pluginsApi } from '@/services/api/plugins';

const mockedApi = vi.mocked(pluginsApi);

const WORKSPACE_ID = 'ws-1';

const mockInstalled: InstalledPlugin = {
  id: 'p-1',
  workspace_id: WORKSPACE_ID,
  repo_url: 'https://github.com/org/skills',
  skill_name: 'code-review',
  display_name: 'Code Review',
  description: 'Reviews pull requests',
  installed_sha: 'abc12345',
  is_active: true,
  has_update: false,
};

const mockAvailable: AvailablePlugin = {
  skill_name: 'test-gen',
  display_name: 'Test Generator',
  description: 'Generates unit tests',
  repo_url: 'https://github.com/org/skills',
};

describe('PluginsStore', () => {
  let store: PluginsStore;

  beforeEach(() => {
    store = new PluginsStore();
    vi.clearAllMocks();
  });

  describe('loadInstalledPlugins', () => {
    it('populates installedPlugins from API response', async () => {
      mockedApi.getInstalled.mockResolvedValue([mockInstalled]);

      await store.loadInstalledPlugins(WORKSPACE_ID);

      expect(mockedApi.getInstalled).toHaveBeenCalledWith(WORKSPACE_ID);
      expect(store.installedPlugins).toEqual([mockInstalled]);
      expect(store.isLoading).toBe(false);
    });

    it('sets error on failure', async () => {
      mockedApi.getInstalled.mockRejectedValue(new Error('Network error'));

      await store.loadInstalledPlugins(WORKSPACE_ID);

      expect(store.error).toBe('Network error');
      expect(store.isLoading).toBe(false);
    });
  });

  describe('fetchRepo', () => {
    it('SKRG-01: populates availablePlugins from GitHub API response', async () => {
      mockedApi.browse.mockResolvedValue([mockAvailable]);

      await store.fetchRepo(WORKSPACE_ID, 'https://github.com/org/skills');

      expect(mockedApi.browse).toHaveBeenCalledWith(WORKSPACE_ID, 'https://github.com/org/skills');
      expect(store.availablePlugins).toEqual([mockAvailable]);
      expect(store.repoError).toBeNull();
    });

    it('SKRG-01: sets repoError when GitHub is unreachable', async () => {
      mockedApi.browse.mockRejectedValue(new Error('GitHub unreachable'));

      await store.fetchRepo(WORKSPACE_ID, 'https://github.com/org/skills');

      expect(store.repoError).toBe('GitHub unreachable');
      expect(store.availablePlugins).toEqual([]);
    });

    it('clears previous availablePlugins on error', async () => {
      // First successful fetch
      mockedApi.browse.mockResolvedValueOnce([mockAvailable]);
      await store.fetchRepo(WORKSPACE_ID, 'https://github.com/org/skills');
      expect(store.availablePlugins).toHaveLength(1);

      // Second fetch fails
      mockedApi.browse.mockRejectedValueOnce(new Error('fail'));
      await store.fetchRepo(WORKSPACE_ID, 'https://github.com/bad/repo');

      expect(store.availablePlugins).toEqual([]);
      expect(store.repoError).toBe('fail');
    });
  });

  describe('installPlugin', () => {
    it('SKRG-02: adds plugin to installedPlugins on success', async () => {
      mockedApi.install.mockResolvedValue(mockInstalled);

      await store.installPlugin(WORKSPACE_ID, 'https://github.com/org/skills', 'code-review');

      expect(mockedApi.install).toHaveBeenCalledWith(WORKSPACE_ID, {
        repo_url: 'https://github.com/org/skills',
        skill_name: 'code-review',
      });
      expect(store.installedPlugins).toContainEqual(mockInstalled);
    });

    it('sets error on install failure', async () => {
      mockedApi.install.mockRejectedValue(new Error('Install failed'));

      await store.installPlugin(WORKSPACE_ID, 'https://github.com/org/skills', 'code-review');

      expect(store.error).toBe('Install failed');
    });
  });

  describe('uninstallPlugin', () => {
    it('removes plugin from installedPlugins on success', async () => {
      store.installedPlugins = [mockInstalled];
      mockedApi.uninstall.mockResolvedValue(undefined);

      await store.uninstallPlugin(WORKSPACE_ID, 'p-1');

      expect(mockedApi.uninstall).toHaveBeenCalledWith(WORKSPACE_ID, 'p-1');
      expect(store.installedPlugins).toEqual([]);
    });
  });

  describe('checkUpdates', () => {
    it('SKRG-04: sets has_update flag on plugins with differing SHA', async () => {
      const updatedPlugin = { ...mockInstalled, has_update: true };
      mockedApi.checkUpdates.mockResolvedValue({ plugins: [updatedPlugin] });
      store.installedPlugins = [mockInstalled];

      await store.checkUpdates(WORKSPACE_ID);

      expect(store.installedPlugins[0]?.has_update).toBe(true);
    });
  });

  describe('GitHub credential', () => {
    it('loadGitHubCredential sets hasGitHubPat', async () => {
      mockedApi.getGitHubCredential.mockResolvedValue({ has_pat: true });

      await store.loadGitHubCredential(WORKSPACE_ID);

      expect(store.hasGitHubPat).toBe(true);
    });

    it('saveGitHubPat calls API and updates hasGitHubPat', async () => {
      mockedApi.saveGitHubPat.mockResolvedValue(undefined);

      await store.saveGitHubPat(WORKSPACE_ID, 'ghp_test123');

      expect(mockedApi.saveGitHubPat).toHaveBeenCalledWith(WORKSPACE_ID, 'ghp_test123');
      expect(store.hasGitHubPat).toBe(true);
    });
  });

  describe('AIStore integration', () => {
    it('AIStore.plugins is an instance of PluginsStore', async () => {
      const { AIStore } = await import('../AIStore');
      const aiStore = new AIStore();
      expect(aiStore.plugins).toBeInstanceOf(PluginsStore);
    });
  });

  describe('reset', () => {
    it('resets all state', () => {
      store.installedPlugins = [mockInstalled];
      store.availablePlugins = [mockAvailable];
      store.isLoading = true;
      store.error = 'some error';
      store.repoError = 'repo error';
      store.hasGitHubPat = true;

      store.reset();

      expect(store.installedPlugins).toEqual([]);
      expect(store.availablePlugins).toEqual([]);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
      expect(store.repoError).toBeNull();
      expect(store.hasGitHubPat).toBe(false);
    });
  });
});
