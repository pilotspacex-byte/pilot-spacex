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
  },
}));

import { mcpServersApi } from '@/services/api/mcp-servers';

const WORKSPACE_ID = 'ws-test-id';

const makeMockServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'server-1',
  workspace_id: WORKSPACE_ID,
  display_name: 'Test MCP',
  url: 'https://example.com/sse',
  auth_type: 'bearer',
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
      status: 'connected',
      checked_at: '2026-01-01T01:00:00Z',
    });

    await store.refreshStatus(WORKSPACE_ID, 'server-1');

    expect(mcpServersApi.checkStatus).toHaveBeenCalledWith(WORKSPACE_ID, 'server-1');
    expect(store.servers[0]?.last_status).toBe('connected');
    expect(store.servers[0]?.last_status_checked_at).toBe('2026-01-01T01:00:00Z');
  });
});
