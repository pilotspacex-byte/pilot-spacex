/**
 * MCP Catalog API client.
 *
 * Phase 35 Plan 02: Typed API client for the public MCP catalog endpoint.
 * GET /mcp-catalog — returns paginated list of catalog entries.
 */
import { apiClient } from '@/services/api/client';

// ============================================================
// Domain types
// ============================================================

export interface McpCatalogEntry {
  id: string;
  name: string;
  description: string;
  url_template: string;
  transport_type: 'sse' | 'http';
  auth_type: 'bearer' | 'oauth2';
  catalog_version: string;
  is_official: boolean;
  icon_url: string | null;
  setup_instructions: string | null;
  sort_order: number;
  oauth_auth_url: string | null;
  oauth_token_url: string | null;
  oauth_scopes: string | null;
}

export interface McpCatalogListResponse {
  items: McpCatalogEntry[];
  total: number;
}

// ============================================================
// API client
// ============================================================

export const mcpCatalogApi = {
  /**
   * List all catalog entries.
   * GET /mcp-catalog
   */
  list: (): Promise<McpCatalogListResponse> =>
    apiClient.get<McpCatalogListResponse>('/mcp-catalog'),
};
