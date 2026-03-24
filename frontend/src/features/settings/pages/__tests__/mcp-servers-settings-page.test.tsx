/**
 * Tests for MCPServersSettingsPage - Phase 25 redeveloped page.
 *
 * Verifies: OAuth callback handling, load on mount, polling interval,
 * empty state, table rendering, and dialog integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const { mockToast, mockMcpStore, mockWorkspaceStore, mockSearchParamsHolder } = vi.hoisted(() => {
  const _mockToast = {
    success: vi.fn(),
    error: vi.fn(),
  };

  const _mockMcpStore = {
    servers: [] as Array<Record<string, unknown>>,
    filteredServers: [] as Array<Record<string, unknown>>,
    isLoading: false,
    isSaving: false,
    isTesting: false,
    error: null as string | null,
    filter: { serverType: 'all', status: 'all', search: '' },
    loadServers: vi.fn(),
    registerServer: vi.fn(),
    removeServer: vi.fn(),
    refreshStatus: vi.fn(),
    getOAuthUrl: vi.fn(),
    updateServer: vi.fn(),
    testConnection: vi.fn(),
    enableServer: vi.fn(),
    disableServer: vi.fn(),
    importServers: vi.fn(),
    setFilter: vi.fn(),
  };

  const _mockWorkspaceStore = {
    getWorkspaceBySlug: vi.fn().mockReturnValue({
      id: 'ws-1',
      name: 'Test',
      slug: 'test-workspace',
    }),
  };

  const _mockSearchParamsHolder = {
    current: new URLSearchParams(),
  };

  return {
    mockToast: _mockToast,
    mockMcpStore: _mockMcpStore,
    mockWorkspaceStore: _mockWorkspaceStore,
    mockSearchParamsHolder: _mockSearchParamsHolder,
  };
});

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useSearchParams: () => mockSearchParamsHolder.current,
}));

vi.mock('sonner', () => ({
  toast: mockToast,
}));

vi.mock('@/stores', () => ({
  useStore: () => ({
    ai: { mcpServers: mockMcpStore },
    workspaceStore: mockWorkspaceStore,
  }),
}));

vi.mock('@/features/settings/components/mcp-servers-table', () => ({
  MCPServersTable: () => <div data-testid="mcp-servers-table">MCPServersTable</div>,
}));

vi.mock('@/features/settings/components/mcp-server-dialog', () => ({
  MCPServerDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="mcp-server-dialog">MCPServerDialog</div> : null,
}));

import { MCPServersSettingsPage } from '@/features/settings/pages/mcp-servers-settings-page';

describe('MCPServersSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockSearchParamsHolder.current = new URLSearchParams();
    mockMcpStore.servers = [];
    mockMcpStore.filteredServers = [];
    mockMcpStore.isLoading = false;
    mockMcpStore.error = null;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('calls loadServers on mount', () => {
    render(<MCPServersSettingsPage />);
    expect(mockMcpStore.loadServers).toHaveBeenCalledWith('ws-1');
  });

  it('shows success toast when URL has ?status=connected', () => {
    mockSearchParamsHolder.current = new URLSearchParams('status=connected');
    render(<MCPServersSettingsPage />);
    expect(mockToast.success).toHaveBeenCalledWith('MCP server authorized successfully');
  });

  it('shows error toast with reason when URL has ?status=error&reason=invalid_state', () => {
    mockSearchParamsHolder.current = new URLSearchParams('status=error&reason=invalid_state');
    render(<MCPServersSettingsPage />);
    expect(mockToast.error).toHaveBeenCalledWith('OAuth authorization failed: invalid_state');
  });

  it('shows error toast with fallback message when reason is missing', () => {
    mockSearchParamsHolder.current = new URLSearchParams('status=error');
    render(<MCPServersSettingsPage />);
    expect(mockToast.error).toHaveBeenCalledWith('OAuth authorization failed: Unknown error');
  });

  it('shows loading skeleton when isLoading and no servers', () => {
    mockMcpStore.isLoading = true;
    mockMcpStore.servers = [];
    render(<MCPServersSettingsPage />);
    // Skeleton uses role-less divs, check that table is not rendered
    expect(screen.queryByTestId('mcp-servers-table')).not.toBeInTheDocument();
  });

  it('shows empty state when no servers and not loading', () => {
    mockMcpStore.servers = [];
    mockMcpStore.isLoading = false;
    render(<MCPServersSettingsPage />);
    expect(screen.getByText('No MCP servers configured yet')).toBeInTheDocument();
  });

  it('renders table when servers exist', () => {
    mockMcpStore.servers = [{ id: 'srv-1', display_name: 'Test' }];
    mockMcpStore.filteredServers = [{ id: 'srv-1', display_name: 'Test' }];
    render(<MCPServersSettingsPage />);
    expect(screen.getByTestId('mcp-servers-table')).toBeInTheDocument();
  });

  it('shows error alert when error and no servers', () => {
    mockMcpStore.error = 'Network failure';
    mockMcpStore.servers = [];
    render(<MCPServersSettingsPage />);
    expect(screen.getByText('Failed to load MCP servers')).toBeInTheDocument();
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  it('sets up 30s polling interval', () => {
    render(<MCPServersSettingsPage />);
    // Initial call
    expect(mockMcpStore.loadServers).toHaveBeenCalledTimes(1);

    // Advance 30s - should trigger another load
    vi.advanceTimersByTime(30_000);
    expect(mockMcpStore.loadServers).toHaveBeenCalledTimes(2);

    // Advance another 30s
    vi.advanceTimersByTime(30_000);
    expect(mockMcpStore.loadServers).toHaveBeenCalledTimes(3);
  });
});
