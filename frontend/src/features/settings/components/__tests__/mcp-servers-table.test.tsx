/**
 * Tests for MCPServersTable - Phase 25 data table component.
 *
 * Verifies: table rendering with server rows, filter bar controls,
 * status badge per status, empty filter results, footer count.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPServersTable } from '../mcp-servers-table';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

const makeServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'srv-1',
  workspace_id: 'ws-1',
  display_name: 'Test Server',
  url: 'https://mcp.example.com',
  server_type: 'remote',
  command_runner: null,
  transport: 'sse',
  url_or_command: 'https://mcp.example.com',
  command_args: null,
  auth_type: 'bearer',
  has_auth_secret: false,
  has_headers: false,
  has_headers_encrypted: false,
  has_env_secret: false,
  is_enabled: true,
  last_status: 'enabled',
  last_status_checked_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const defaultProps = {
  servers: [] as MCPServer[],
  totalCount: 0,
  filterType: 'all' as const,
  filterStatus: 'all' as const,
  filterSearch: '',
  onFilterTypeChange: vi.fn(),
  onFilterStatusChange: vi.fn(),
  onFilterSearchChange: vi.fn(),
  onEdit: vi.fn(),
  onTestConnection: vi.fn(),
  onToggleEnabled: vi.fn(),
  onDelete: vi.fn(),
  deletingServerId: null,
  testingServerId: null,
};

describe('MCPServersTable', () => {
  it('renders table headers', () => {
    render(<MCPServersTable {...defaultProps} />);
    expect(screen.getByText('Server Name')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('URL / Command')).toBeInTheDocument();
    expect(screen.getByText('Transport')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('shows empty filter message when no servers', () => {
    render(<MCPServersTable {...defaultProps} />);
    expect(screen.getByText('No servers match the current filters.')).toBeInTheDocument();
  });

  it('renders server rows with correct data', () => {
    const servers = [
      makeServer({ id: 'srv-1', display_name: 'Alpha Server', server_type: 'remote', transport: 'sse' }),
      makeServer({ id: 'srv-2', display_name: 'Beta Server', server_type: 'command', command_runner: 'npx', transport: 'stdio', url_or_command: '@mcp/server' }),
    ];
    render(<MCPServersTable {...defaultProps} servers={servers} totalCount={2} />);

    expect(screen.getByText('Alpha Server')).toBeInTheDocument();
    expect(screen.getByText('Beta Server')).toBeInTheDocument();
    expect(screen.getByText('@mcp/server')).toBeInTheDocument();
  });

  it('renders status badge with correct label per status', () => {
    const servers = [
      makeServer({ id: 'srv-1', display_name: 'Enabled Server', last_status: 'enabled' }),
      makeServer({ id: 'srv-2', display_name: 'Disabled Server', last_status: 'disabled', is_enabled: false }),
      makeServer({ id: 'srv-3', display_name: 'Unhealthy Server', last_status: 'unhealthy' }),
    ];
    render(<MCPServersTable {...defaultProps} servers={servers} totalCount={3} />);

    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(screen.getByText('Unhealthy')).toBeInTheDocument();
  });

  it('renders footer count reflecting filtered/total counts', () => {
    const servers = [makeServer()];
    render(<MCPServersTable {...defaultProps} servers={servers} totalCount={5} />);
    expect(screen.getByText('Showing 1 of 5 servers')).toBeInTheDocument();
  });

  it('calls onFilterSearchChange when typing in search input', async () => {
    const user = userEvent.setup();
    const onFilterSearchChange = vi.fn();
    render(<MCPServersTable {...defaultProps} onFilterSearchChange={onFilterSearchChange} />);

    const searchInput = screen.getByPlaceholderText('Search servers...');
    await user.type(searchInput, 'test');

    expect(onFilterSearchChange).toHaveBeenCalled();
  });

  it('renders ServerTypeBadge for each server type', () => {
    const servers = [
      makeServer({ id: 'srv-1', server_type: 'remote' }),
      makeServer({ id: 'srv-2', server_type: 'command', command_runner: 'npx' }),
      makeServer({ id: 'srv-3', server_type: 'command', command_runner: 'uvx' }),
    ];
    render(<MCPServersTable {...defaultProps} servers={servers} totalCount={3} />);

    expect(screen.getByText('Remote')).toBeInTheDocument();
    // command_runner labels shown: 'npx' and 'uvx'
    expect(screen.getByText('npx')).toBeInTheDocument();
    expect(screen.getByText('uvx')).toBeInTheDocument();
  });

  it('renders TransportBadge for each server', () => {
    const servers = [
      makeServer({ id: 'srv-1', transport: 'sse' }),
      makeServer({ id: 'srv-2', transport: 'stdio' }),
    ];
    render(<MCPServersTable {...defaultProps} servers={servers} totalCount={2} />);

    expect(screen.getByText('sse')).toBeInTheDocument();
    expect(screen.getByText('stdio')).toBeInTheDocument();
  });
});
