/**
 * PluginsStore - MobX observable store for workspace plugin management.
 *
 * Phase 19 Plan 04: Manages installed and available plugins including
 * browsing GitHub repos, installing/uninstalling, checking for updates,
 * and GitHub PAT credential management.
 *
 * Pattern: mirrors MCPServersStore pattern exactly.
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { pluginsApi } from '@/services/api/plugins';

// ============================================================
// Domain types (exported — imported by plugins API client)
// ============================================================

export interface InstalledPlugin {
  id: string;
  workspace_id: string;
  repo_url: string;
  skill_name: string;
  display_name: string;
  description: string | null;
  installed_sha: string;
  is_active: boolean;
  has_update: boolean;
}

export interface AvailablePlugin {
  skill_name: string;
  display_name: string;
  description: string | null;
  repo_url: string;
}

// ============================================================
// Store
// ============================================================

export class PluginsStore {
  installedPlugins: InstalledPlugin[] = [];
  availablePlugins: AvailablePlugin[] = [];
  isLoading = false;
  isSaving = false;
  isCheckingUpdates = false;
  error: string | null = null;
  repoError: string | null = null;
  hasGitHubPat = false;
  selectedPlugin: InstalledPlugin | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async loadInstalledPlugins(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const data = await pluginsApi.getInstalled(workspaceId);
      runInAction(() => {
        this.installedPlugins = data;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load plugins';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  }

  async fetchRepo(workspaceId: string, repoUrl: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.repoError = null;
    });

    try {
      const data = await pluginsApi.browse(workspaceId, repoUrl);
      runInAction(() => {
        this.availablePlugins = data;
      });
    } catch (err) {
      runInAction(() => {
        this.availablePlugins = [];
        this.repoError = err instanceof Error ? err.message : 'Failed to browse repository';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  }

  async installPlugin(workspaceId: string, repoUrl: string, skillName: string): Promise<void> {
    runInAction(() => {
      this.isSaving = true;
      this.error = null;
    });

    try {
      const plugin = await pluginsApi.install(workspaceId, {
        repo_url: repoUrl,
        skill_name: skillName,
      });
      runInAction(() => {
        this.installedPlugins = [...this.installedPlugins, plugin];
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to install plugin';
        this.isSaving = false;
      });
    }
  }

  async uninstallPlugin(workspaceId: string, pluginId: string): Promise<void> {
    try {
      await pluginsApi.uninstall(workspaceId, pluginId);
      runInAction(() => {
        this.installedPlugins = this.installedPlugins.filter((p) => p.id !== pluginId);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to uninstall plugin';
      });
    }
  }

  async checkUpdates(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isCheckingUpdates = true;
    });

    try {
      const result = await pluginsApi.checkUpdates(workspaceId);
      runInAction(() => {
        // Update has_update flag on matching installed plugins
        this.installedPlugins = this.installedPlugins.map((installed) => {
          const updated = result.plugins.find((p) => p.id === installed.id);
          return updated ? { ...installed, has_update: updated.has_update } : installed;
        });
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to check for updates';
      });
    } finally {
      runInAction(() => {
        this.isCheckingUpdates = false;
      });
    }
  }

  async saveGitHubPat(workspaceId: string, pat: string): Promise<void> {
    runInAction(() => {
      this.isSaving = true;
      this.error = null;
    });

    try {
      await pluginsApi.saveGitHubPat(workspaceId, pat);
      runInAction(() => {
        this.hasGitHubPat = true;
        this.isSaving = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to save GitHub PAT';
        this.isSaving = false;
      });
    }
  }

  async loadGitHubCredential(workspaceId: string): Promise<void> {
    try {
      const result = await pluginsApi.getGitHubCredential(workspaceId);
      runInAction(() => {
        this.hasGitHubPat = result.has_pat;
      });
    } catch {
      // Silent — hasGitHubPat stays false
    }
  }

  setSelectedPlugin(plugin: InstalledPlugin | null): void {
    this.selectedPlugin = plugin;
  }

  reset(): void {
    this.installedPlugins = [];
    this.availablePlugins = [];
    this.isLoading = false;
    this.isSaving = false;
    this.isCheckingUpdates = false;
    this.error = null;
    this.repoError = null;
    this.hasGitHubPat = false;
    this.selectedPlugin = null;
  }
}
