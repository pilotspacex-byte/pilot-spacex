/**
 * Tests for MCPServersStore - MobX observable store for workspace MCP servers.
 *
 * These tests verify the behavioral contract:
 *   - loadServers() populates servers observable from API response
 *   - loadServers() sets error on API failure; servers stays empty
 *   - registerServer() calls POST and reloads list on success
 *   - removeServer() calls DELETE and removes from servers list
 *   - refreshStatus() calls GET .../status and updates matching server status field
 *
 * Pattern: mirrors AISettingsStore.test.ts (vi.mock for mcpServersApi).
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { MCPServersStore } from '../MCPServersStore';
import type { MCPServer } from '../MCPServersStore';

vi.mock('@/services/api/mcp-servers', () => ({
  mcpServersApi: {
    list: vi.fn(),
    register: vi.fn(),
    checkStatus: vi.fn(),
    remove: vi.fn(),
    getOAuthUrl: vi.fn(),
    update: vi.fn(),
    testConnection: vi.fn(),
    enable: vi.fn(),
    disable: vi.fn(),
    importServers: vi.fn(),
  },
}));

import { mcpServersApi } from '@/services/api/mcp-servers';

const WORKSPACE_ID = 'ws-test-id';

const makeMockServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'server-1',
  workspace_id: WORKSPACE_ID,
  display_name: 'Test MCP',
  url: 'https://example.com/sse',
  server_type: 'remote',
  command_runner: null,
  transport: 'sse',
  url_or_command: 'https://example.com/sse',
  command_args: null,
  auth_type: 'bearer',
  has_auth_secret: false,
  has_headers: false,
  has_headers_encrypted: false,
  has_env_secret: false,
  is_enabled: true,
  last_status: null,
  last_status_checked_at: null,
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('MCPServersStore', () => {
  let store: MCPServersStore;

  beforeEach(() => {
    store = new MCPServersStore();
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loadServers() fetches from GET /workspaces/{id}/mcp-servers and populates servers observable', async () => {
    const mockServers = [
      makeMockServer(),
      makeMockServer({ id: 'server-2', display_name: 'MCP 2' }),
    ];
    vi.mocked(mcpServersApi.list).mockResolvedValueOnce({ items: mockServers, total: 2 });

    await store.loadServers(WORKSPACE_ID);

    expect(mcpServersApi.list).toHaveBeenCalledWith(WORKSPACE_ID);
    expect(store.servers).toHaveLength(2);
    expect(store.servers[0]?.display_name).toBe('Test MCP');
    expect(store.servers[1]?.display_name).toBe('MCP 2');
  });

  it('loadServers() sets isLoading=true during fetch and isLoading=false after completion', async () => {
    const isLoadingStates: boolean[] = [];
    vi.mocked(mcpServersApi.list).mockImplementationOnce(async () => {
      isLoadingStates.push(store.isLoading);
      return { items: [], total: 0 };
    });

    await store.loadServers(WORKSPACE_ID);

    expect(isLoadingStates[0]).toBe(true);
    expect(store.isLoading).toBe(false);
  });

  it('loadServers() sets error string on API failure; servers remains empty array', async () => {
    vi.mocked(mcpServersApi.list).mockRejectedValueOnce(new Error('Network error'));

    await store.loadServers(WORKSPACE_ID);

    expect(store.error).toBe('Network error');
    expect(store.servers).toHaveLength(0);
    expect(store.isLoading).toBe(false);
  });

  it('registerServer() calls POST /workspaces/{id}/mcp-servers with payload, then appends to servers list', async () => {
    const newServer = makeMockServer({ id: 'new-server' });
    vi.mocked(mcpServersApi.register).mockResolvedValueOnce(newServer);

    const registerData = {
      display_name: 'Test MCP',
      url: 'https://example.com/sse',
      auth_type: 'bearer' as const,
      auth_token: 'tok-123',
    };

    await store.registerServer(WORKSPACE_ID, registerData);

    expect(mcpServersApi.register).toHaveBeenCalledWith(WORKSPACE_ID, registerData);
    expect(store.servers).toHaveLength(1);
    expect(store.servers[0]?.id).toBe('new-server');
    expect(store.error).toBeNull();
  });

  it('removeServer() calls DELETE /workspaces/{id}/mcp-servers/{serverId}, removes entry from servers observable', async () => {
    // Pre-populate store
    vi.mocked(mcpServersApi.list).mockResolvedValueOnce({
      items: [makeMockServer({ id: 'server-1' }), makeMockServer({ id: 'server-2' })],
      total: 2,
    });
    await store.loadServers(WORKSPACE_ID);
    expect(store.servers).toHaveLength(2);

    vi.mocked(mcpServersApi.remove).mockResolvedValueOnce(undefined);
    await store.removeServer(WORKSPACE_ID, 'server-1');

    expect(mcpServersApi.remove).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1');
    expect(store.servers).toHaveLength(1);
    expect(store.servers[0]?.id).toBe('server-2');
  });

  it('refreshStatus() calls GET .../status and updates matching server status field in servers observable', async () => {
    // Pre-populate store with a server with unknown status
    vi.mocked(mcpServersApi.list).mockResolvedValueOnce({
      items: [makeMockServer({ id: 'server-1', last_status: null })],
      total: 1,
    });
    await store.loadServers(WORKSPACE_ID);

    vi.mocked(mcpServersApi.checkStatus).mockResolvedValueOnce({
      server_id: 'server-1',
      status: 'enabled',
      checked_at: '2026-01-01T01:00:00Z',
    });

    await store.refreshStatus(WORKSPACE_ID, 'server-1');

    expect(mcpServersApi.checkStatus).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1');
    expect(store.servers[0]?.last_status).toBe('enabled');
    expect(store.servers[0]?.last_status_checked_at).toBe('2026-01-01T01:00:00Z');
  });

  it('updateServer() updates matching server and resets isSaving on success', async () => {
    store.servers = [makeMockServer({ id: 'server-1', display_name: 'Old Name' })];
    const updated = makeMockServer({ id: 'server-1', display_name: 'Updated Name' });
    vi.mocked(mcpServersApi.update).mockResolvedValueOnce(updated);

    await store.updateServer(WORKSPACE_ID, 'server-1', { display_name: 'Updated Name' });

    expect(mcpServersApi.update).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1', {
      display_name: 'Updated Name',
    });
    expect(store.servers[0]?.display_name).toBe('Updated Name');
    expect(store.isSaving).toBe(false);
  });

  it('updateServer() sets error and rethrows on failure', async () => {
    store.servers = [makeMockServer({ id: 'server-1', display_name: 'Old Name' })];
    vi.mocked(mcpServersApi.update).mockRejectedValueOnce(new Error('Update failed'));

    await expect(
      store.updateServer(WORKSPACE_ID, 'server-1', { display_name: 'Updated Name' })
    ).rejects.toThrow('Update failed');

    expect(store.error).toBe('Update failed');
    expect(store.servers[0]?.display_name).toBe('Old Name');
    expect(store.isSaving).toBe(false);
  });

  it('testConnection() updates last_status and last_status_checked_at on success', async () => {
    store.servers = [makeMockServer({ id: 'server-1', last_status: null, last_status_checked_at: null })];
    vi.mocked(mcpServersApi.testConnection).mockResolvedValueOnce({
      server_id: 'server-1',
      status: 'enabled',
      latency_ms: 8,
      checked_at: '2026-01-01T02:00:00Z',
      error_detail: null,
    });

    const result = await store.testConnection(WORKSPACE_ID, 'server-1');

    expect(result.status).toBe('enabled');
    expect(store.servers[0]?.last_status).toBe('enabled');
    expect(store.servers[0]?.last_status_checked_at).toBe('2026-01-01T02:00:00Z');
  });

  it('testConnection() sets error and rethrows on failure', async () => {
    store.servers = [makeMockServer({ id: 'server-1', last_status: null, last_status_checked_at: null })];
    vi.mocked(mcpServersApi.testConnection).mockRejectedValueOnce(new Error('Connection failed'));

    await expect(store.testConnection(WORKSPACE_ID, 'server-1')).rejects.toThrow('Connection failed');

    expect(store.error).toBe('Connection failed');
    expect(store.servers[0]?.last_status).toBeNull();
  });

  it('enableServer() applies optimistic enabled state and keeps it on success', async () => {
    store.servers = [makeMockServer({ id: 'server-1', is_enabled: false, last_status: 'disabled' })];

    let resolveEnable: (() => void) | undefined;
    vi.mocked(mcpServersApi.enable).mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveEnable = resolve;
        })
    );

    const enablePromise = store.enableServer(WORKSPACE_ID, 'server-1');

    expect(store.servers[0]?.is_enabled).toBe(true);
    expect(store.servers[0]?.last_status).toBe('enabled');

    resolveEnable?.();
    await enablePromise;

    expect(mcpServersApi.enable).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1');
    expect(store.servers[0]?.is_enabled).toBe(true);
    expect(store.servers[0]?.last_status).toBe('enabled');
  });

  it('enableServer() reverts optimistic update and sets error on failure', async () => {
    store.servers = [makeMockServer({ id: 'server-1', is_enabled: false, last_status: 'disabled' })];
    vi.mocked(mcpServersApi.enable).mockRejectedValueOnce(new Error('Enable failed'));

    await expect(store.enableServer(WORKSPACE_ID, 'server-1')).rejects.toThrow('Enable failed');

    expect(store.servers[0]?.is_enabled).toBe(false);
    expect(store.servers[0]?.last_status).toBe('disabled');
    expect(store.error).toBe('Enable failed');
  });

  it('disableServer() applies optimistic disabled state and keeps it on success', async () => {
    store.servers = [makeMockServer({ id: 'server-1', is_enabled: true, last_status: 'enabled' })];

    let resolveDisable: (() => void) | undefined;
    vi.mocked(mcpServersApi.disable).mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveDisable = resolve;
        })
    );

    const disablePromise = store.disableServer(WORKSPACE_ID, 'server-1');

    expect(store.servers[0]?.is_enabled).toBe(false);
    expect(store.servers[0]?.last_status).toBe('disabled');

    resolveDisable?.();
    await disablePromise;

    expect(mcpServersApi.disable).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1');
    expect(store.servers[0]?.is_enabled).toBe(false);
    expect(store.servers[0]?.last_status).toBe('disabled');
  });

  it('disableServer() reverts optimistic update and sets error on failure', async () => {
    store.servers = [makeMockServer({ id: 'server-1', is_enabled: true, last_status: 'enabled' })];
    vi.mocked(mcpServersApi.disable).mockRejectedValueOnce(new Error('Disable failed'));

    await expect(store.disableServer(WORKSPACE_ID, 'server-1')).rejects.toThrow('Disable failed');

    expect(store.servers[0]?.is_enabled).toBe(true);
    expect(store.servers[0]?.last_status).toBe('enabled');
    expect(store.error).toBe('Disable failed');
  });

  it('importServers() imports, reloads list, and resets isSaving on success', async () => {
    const importResult = {
      imported: [{ name: 'context7', id: 'server-1' }],
      skipped: [],
      errors: [],
    };
    vi.mocked(mcpServersApi.importServers).mockResolvedValueOnce(importResult);
    vi.mocked(mcpServersApi.list).mockResolvedValueOnce({
      items: [makeMockServer({ id: 'server-1', display_name: 'context7' })],
      total: 1,
    });

    const result = await store.importServers(WORKSPACE_ID, '{"mcpServers":{}}');

    expect(mcpServersApi.importServers).toHaveBeenCalledWith(WORKSPACE_ID, '{"mcpServers":{}}');
    expect(mcpServersApi.list).toHaveBeenCalledWith(WORKSPACE_ID);
    expect(store.servers).toHaveLength(1);
    expect(store.servers[0]?.display_name).toBe('context7');
    expect(store.isSaving).toBe(false);
    expect(result).toEqual(importResult);
  });

  it('importServers() sets error, resets isSaving, and rethrows on failure', async () => {
    vi.mocked(mcpServersApi.importServers).mockRejectedValueOnce(new Error('Import failed'));

    await expect(store.importServers(WORKSPACE_ID, '{"mcpServers":{}}')).rejects.toThrow('Import failed');

    expect(store.error).toBe('Import failed');
    expect(store.isSaving).toBe(false);
  });

  it('filteredServers filters by serverType', () => {
    store.servers = [
      makeMockServer({ id: 'remote-1', server_type: 'remote' }),
      makeMockServer({ id: 'command-1', server_type: 'command', command_runner: 'npx' }),
    ];

    store.setFilter({ serverType: 'remote' });

    expect(store.filteredServers).toHaveLength(1);
    expect(store.filteredServers[0]?.id).toBe('remote-1');
  });

  it('filteredServers filters by status', () => {
    store.servers = [
      makeMockServer({ id: 's1', last_status: 'enabled' }),
      makeMockServer({ id: 's2', last_status: 'disabled' }),
    ];

    store.setFilter({ status: 'enabled' });

    expect(store.filteredServers).toHaveLength(1);
    expect(store.filteredServers[0]?.id).toBe('s1');
  });

  it('filteredServers search matches display_name and url_or_command', () => {
    store.servers = [
      makeMockServer({ id: 's1', display_name: 'Context Seven', url_or_command: 'https://example.com' }),
      makeMockServer({ id: 's2', display_name: 'Other', url_or_command: '@context7/mcp' }),
      makeMockServer({ id: 's3', display_name: 'Unrelated', url_or_command: '@foo/bar' }),
    ];

    store.setFilter({ search: 'context' });

    expect(store.filteredServers.map((s) => s.id)).toEqual(['s1', 's2']);
  });

  it('filteredServers applies combined type + status filters as intersection', () => {
    store.servers = [
      makeMockServer({ id: 's1', server_type: 'remote', last_status: 'enabled' }),
      makeMockServer({ id: 's2', server_type: 'remote', last_status: 'disabled' }),
      makeMockServer({ id: 's3', server_type: 'command', command_runner: 'npx', last_status: 'enabled' }),
    ];

    store.setFilter({ serverType: 'remote', status: 'enabled' });

    expect(store.filteredServers).toHaveLength(1);
    expect(store.filteredServers[0]?.id).toBe('s1');
  });

  it('setFilter() partial update only changes provided keys', () => {
    expect(store.filter).toEqual({ serverType: 'all', status: 'all', search: '' });

    store.setFilter({ search: 'context' });

    expect(store.filter.search).toBe('context');
    expect(store.filter.serverType).toBe('all');
    expect(store.filter.status).toBe('all');
  });
});
