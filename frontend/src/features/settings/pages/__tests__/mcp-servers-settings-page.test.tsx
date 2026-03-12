/**
 * Tests for MCPServersSettingsPage OAuth2 callback and authorize flow.
 *
 * Phase 22 Plan 02: OAuth callback status handling and authorize handler.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// vi.hoisted runs before vi.mock hoisting, so these are available in factories
const { mockToast, mockMcpStore, mockWorkspaceStore, mockSearchParamsHolder } = vi.hoisted(() => {
  const _mockToast = {
    success: vi.fn(),
    error: vi.fn(),
  };

  const _mockMcpStore = {
    servers: [] as Array<Record<string, unknown>>,
    isLoading: false,
    isSaving: false,
    error: null as string | null,
    loadServers: vi.fn(),
    registerServer: vi.fn(),
    removeServer: vi.fn(),
    refreshStatus: vi.fn(),
    getOAuthUrl: vi.fn(),
  };

  const _mockWorkspaceStore = {
    getWorkspaceBySlug: vi.fn().mockReturnValue({
      id: 'ws-1',
      name: 'Test',
      slug: 'test-workspace',
    }),
  };

  // Holder object so we can reassign the value inside tests
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

vi.mock('@/features/settings/components/mcp-server-form', () => ({
  MCPServerForm: () => <div data-testid="mcp-server-form">MCPServerForm</div>,
}));

vi.mock('@/features/settings/components/mcp-server-card', () => ({
  MCPServerCard: ({
    server,
    onAuthorize,
  }: {
    server: { id: string; display_name: string };
    onDelete: (id: string) => void;
    onRefreshStatus: (id: string) => void;
    onAuthorize?: (id: string) => void;
    isDeleting: boolean;
  }) => (
    <div data-testid={`server-card-${server.id}`}>
      {server.display_name}
      {onAuthorize && (
        <button data-testid={`authorize-${server.id}`} onClick={() => onAuthorize(server.id)}>
          Authorize
        </button>
      )}
    </div>
  ),
}));

import { MCPServersSettingsPage } from '@/features/settings/pages/mcp-servers-settings-page';

describe('MCPServersSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParamsHolder.current = new URLSearchParams();
    mockMcpStore.servers = [];
    mockMcpStore.isLoading = false;
    mockMcpStore.error = null;
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

  it('calls mcpStore.loadServers after successful OAuth callback', () => {
    mockSearchParamsHolder.current = new URLSearchParams('status=connected');

    render(<MCPServersSettingsPage />);

    expect(mockMcpStore.loadServers).toHaveBeenCalledWith('ws-1');
  });

  it('handleAuthorize calls mcpStore.getOAuthUrl', async () => {
    const user = userEvent.setup();
    mockMcpStore.getOAuthUrl.mockResolvedValue('https://auth.example.com/authorize');
    mockMcpStore.servers = [
      {
        id: 'srv-1',
        workspace_id: 'ws-1',
        display_name: 'OAuth Server',
        url: 'https://mcp.example.com',
        auth_type: 'oauth2',
        last_status: null,
        last_status_checked_at: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(<MCPServersSettingsPage />);

    const authorizeBtn = screen.getByTestId('authorize-srv-1');
    await user.click(authorizeBtn);

    await waitFor(() => {
      expect(mockMcpStore.getOAuthUrl).toHaveBeenCalledWith('ws-1', 'srv-1');
    });
  });

  it('handleAuthorize shows error toast if getOAuthUrl throws', async () => {
    const user = userEvent.setup();
    mockMcpStore.getOAuthUrl.mockRejectedValue(new Error('Network error'));
    mockMcpStore.servers = [
      {
        id: 'srv-2',
        workspace_id: 'ws-1',
        display_name: 'Failing Server',
        url: 'https://fail.example.com',
        auth_type: 'oauth2',
        last_status: null,
        last_status_checked_at: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(<MCPServersSettingsPage />);

    const authorizeBtn = screen.getByTestId('authorize-srv-2');
    await user.click(authorizeBtn);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith('Failed to start OAuth authorization');
    });
  });

  it('passes onAuthorize prop to MCPServerCard components', () => {
    mockMcpStore.servers = [
      {
        id: 'srv-3',
        workspace_id: 'ws-1',
        display_name: 'Test Server',
        url: 'https://test.example.com',
        auth_type: 'oauth2',
        last_status: 'connected',
        last_status_checked_at: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    render(<MCPServersSettingsPage />);

    // The mock MCPServerCard renders an authorize button only when onAuthorize is passed
    expect(screen.getByTestId('authorize-srv-3')).toBeInTheDocument();
  });
});
