/**
 * Tests for MCPCatalogStore - MobX observable store for MCP catalog entries.
 *
 * Behavioral contract:
 *   - mcpCatalogApi.list() calls GET /mcp-catalog and returns McpCatalogListResponse
 *   - MCPCatalogStore.loadCatalog() sets entries from API response (happy path)
 *   - MCPCatalogStore.loadCatalog() sets error on failure, entries stays empty
 *   - MCPCatalogStore.isLoading toggles true during fetch, false after
 *   - hasUpdate(entry, server): returns true only when installed_catalog_version !== null && !== catalog_version
 *   - isInstalled(entry, servers): returns true if any server.catalog_entry_id === entry.id
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { MCPCatalogStore, hasUpdate, isInstalled } from '../MCPCatalogStore';
import type { McpCatalogEntry } from '@/services/api/mcp-catalog';
import type { MCPServer } from '../MCPServersStore';

vi.mock('@/services/api/mcp-catalog', () => ({
  mcpCatalogApi: {
    list: vi.fn(),
  },
}));

import { mcpCatalogApi } from '@/services/api/mcp-catalog';

const makeCatalogEntry = (overrides?: Partial<McpCatalogEntry>): McpCatalogEntry => ({
  id: 'entry-1',
  name: 'Context7',
  description: 'Context7 MCP server for documentation',
  url_template: 'https://mcp.context7.com/mcp',
  transport_type: 'http',
  auth_type: 'bearer',
  catalog_version: '1.0.0',
  is_official: true,
  icon_url: null,
  setup_instructions: null,
  sort_order: 0,
  oauth_auth_url: null,
  oauth_token_url: null,
  oauth_scopes: null,
  ...overrides,
});

const makeMockServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'server-1',
  workspace_id: 'ws-1',
  display_name: 'Context7',
  url: 'https://mcp.context7.com/mcp',
  auth_type: 'bearer',
  last_status: null,
  last_status_checked_at: null,
  token_expires_at: null,
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('MCPCatalogStore', () => {
  let store: MCPCatalogStore;

  beforeEach(() => {
    store = new MCPCatalogStore();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('starts with empty entries, isLoading=false, error=null', () => {
    expect(store.entries).toHaveLength(0);
    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
  });

  it('loadCatalog() sets entries from API response on success', async () => {
    const entries = [makeCatalogEntry(), makeCatalogEntry({ id: 'entry-2', name: 'GitHub' })];
    vi.mocked(mcpCatalogApi.list).mockResolvedValueOnce({ items: entries, total: 2 });

    await store.loadCatalog();

    expect(mcpCatalogApi.list).toHaveBeenCalledTimes(1);
    expect(store.entries).toHaveLength(2);
    expect(store.entries[0]?.name).toBe('Context7');
    expect(store.entries[1]?.name).toBe('GitHub');
    expect(store.error).toBeNull();
  });

  it('loadCatalog() sets isLoading=true during fetch, isLoading=false after completion', async () => {
    const isLoadingDuringFetch: boolean[] = [];
    vi.mocked(mcpCatalogApi.list).mockImplementationOnce(async () => {
      isLoadingDuringFetch.push(store.isLoading);
      return { items: [], total: 0 };
    });

    await store.loadCatalog();

    expect(isLoadingDuringFetch[0]).toBe(true);
    expect(store.isLoading).toBe(false);
  });

  it('loadCatalog() sets error string on API failure; entries remains empty', async () => {
    vi.mocked(mcpCatalogApi.list).mockRejectedValueOnce(new Error('Network timeout'));

    await store.loadCatalog();

    expect(store.error).toBe('Network timeout');
    expect(store.entries).toHaveLength(0);
    expect(store.isLoading).toBe(false);
  });

  it('loadCatalog() sets generic error message for non-Error rejections', async () => {
    vi.mocked(mcpCatalogApi.list).mockRejectedValueOnce('unknown error');

    await store.loadCatalog();

    expect(store.error).toBe('Failed to load catalog');
    expect(store.isLoading).toBe(false);
  });
});

describe('hasUpdate()', () => {
  it('returns false when server has no installed_catalog_version (null)', () => {
    const entry = makeCatalogEntry({ catalog_version: '1.0.0' });
    const server = makeMockServer({ installed_catalog_version: null });
    expect(hasUpdate(entry, server)).toBe(false);
  });

  it('returns false when server has no installed_catalog_version (undefined)', () => {
    const entry = makeCatalogEntry({ catalog_version: '1.0.0' });
    const server = makeMockServer({ installed_catalog_version: undefined });
    expect(hasUpdate(entry, server)).toBe(false);
  });

  it('returns false when installed_catalog_version matches catalog_version', () => {
    const entry = makeCatalogEntry({ catalog_version: '1.0.0' });
    const server = makeMockServer({ installed_catalog_version: '1.0.0' });
    expect(hasUpdate(entry, server)).toBe(false);
  });

  it('returns true when installed_catalog_version differs from catalog_version', () => {
    const entry = makeCatalogEntry({ catalog_version: '2.0.0' });
    const server = makeMockServer({ installed_catalog_version: '1.0.0' });
    expect(hasUpdate(entry, server)).toBe(true);
  });
});

describe('isInstalled()', () => {
  it('returns true when a server has catalog_entry_id matching entry.id', () => {
    const entry = makeCatalogEntry({ id: 'entry-1' });
    const servers = [
      makeMockServer({ catalog_entry_id: 'entry-1' }),
      makeMockServer({ id: 'server-2', catalog_entry_id: 'entry-2' }),
    ];
    expect(isInstalled(entry, servers)).toBe(true);
  });

  it('returns false when no server has matching catalog_entry_id', () => {
    const entry = makeCatalogEntry({ id: 'entry-1' });
    const servers = [
      makeMockServer({ catalog_entry_id: 'entry-99' }),
      makeMockServer({ id: 'server-2', catalog_entry_id: undefined }),
    ];
    expect(isInstalled(entry, servers)).toBe(false);
  });

  it('returns false when servers array is empty', () => {
    const entry = makeCatalogEntry({ id: 'entry-1' });
    expect(isInstalled(entry, [])).toBe(false);
  });
});
