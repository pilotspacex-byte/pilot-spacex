/**
 * Tests for MCPServersStore - MobX observable store for workspace MCP servers.
 *
 * Phase 14 Plan 05 will implement MCPServersStore in
 * frontend/src/stores/ai/MCPServersStore.ts. These stubs define the
 * behavioral contract for that implementation:
 *
 *   - loadServers() populates servers observable from API response
 *   - loadServers() sets error on API failure; servers stays empty
 *   - registerServer() calls POST and reloads list on success
 *   - removeServer() calls DELETE and removes from servers list
 *   - checkStatus() updates server status field
 *
 * All tests use it.todo() - Vitest treats todo tests as pending (Wave 0 state).
 * When plan 14-05 builds MCPServersStore, these are converted to real assertions.
 *
 * Pattern: mirrors AISettingsStore.test.ts (vi.mock for apiClient + aiApi).
 */

import { describe, it } from 'vitest';

// MCPServersStore does not exist yet - import will fail until plan 14-05.
// Using it.todo() so the suite exits 0 in Wave 0 state.
// When the store is implemented, replace it.todo() with:
//
//   import { MCPServersStore } from '../MCPServersStore';
//
// and add vi.mock('@/services/api/mcp-servers', ...) at the top.

describe('MCPServersStore', () => {
  it.todo(
    'loadServers() fetches from GET /workspaces/{id}/mcp-servers and populates servers observable'
  );

  it.todo('loadServers() sets isLoading=true during fetch and isLoading=false after completion');

  it.todo('loadServers() sets error string on API failure; servers remains empty array');

  it.todo(
    'registerServer() calls POST /workspaces/{id}/mcp-servers with payload, then reloads list on success'
  );

  it.todo(
    'removeServer() calls DELETE /workspaces/{id}/mcp-servers/{serverId}, removes entry from servers observable'
  );

  it.todo(
    'checkStatus() calls GET .../status and updates matching server status field in servers observable'
  );
});
