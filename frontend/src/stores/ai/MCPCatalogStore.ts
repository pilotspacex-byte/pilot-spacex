/**
 * MCPCatalogStore - MobX observable store for the public MCP catalog.
 *
 * Phase 35 Plan 02: Loads browsable catalog entries from GET /mcp-catalog.
 * Provides hasUpdate() and isInstalled() utility functions for update detection.
 *
 * Pattern: mirrors MCPServersStore pattern exactly.
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { mcpCatalogApi } from '@/services/api/mcp-catalog';
import type { McpCatalogEntry } from '@/services/api/mcp-catalog';
import type { MCPServer } from './MCPServersStore';

// ============================================================
// Utility functions (exported for use in components and tests)
// ============================================================

/**
 * Returns true if the server has an installed_catalog_version that differs
 * from the catalog entry's current catalog_version (i.e. an update is available).
 *
 * Returns false when installed_catalog_version is null/undefined (not installed from catalog).
 */
export function hasUpdate(entry: McpCatalogEntry, server: MCPServer): boolean {
  if (!server.installed_catalog_version) return false;
  return server.installed_catalog_version !== entry.catalog_version;
}

/**
 * Returns true if any server in the list has a catalog_entry_id matching entry.id.
 */
export function isInstalled(entry: McpCatalogEntry, installedServers: MCPServer[]): boolean {
  return installedServers.some((s) => s.catalog_entry_id === entry.id);
}

// ============================================================
// Store
// ============================================================

export class MCPCatalogStore {
  entries: McpCatalogEntry[] = [];
  isLoading = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async loadCatalog(): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const data = await mcpCatalogApi.list();
      runInAction(() => {
        this.entries = data.items;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load catalog';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  }

  reset(): void {
    this.entries = [];
    this.isLoading = false;
    this.error = null;
  }
}
