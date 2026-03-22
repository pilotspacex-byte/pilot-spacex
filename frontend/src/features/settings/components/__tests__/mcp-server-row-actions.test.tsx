/**
 * Tests for MCPServerRowActions - Phase 25 dropdown menu with actions.
 *
 * Verifies: dropdown menu items, delete AlertDialog, enable/disable toggle label,
 * callback invocations.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPServerRowActions } from '../mcp-server-row-actions';
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
  server: makeServer(),
  onEdit: vi.fn(),
  onTestConnection: vi.fn(),
  onToggleEnabled: vi.fn(),
  onDelete: vi.fn(),
  isDeleting: false,
  isTesting: false,
};

describe('MCPServerRowActions', () => {
  it('renders trigger button with Server actions label', () => {
    render(<MCPServerRowActions {...defaultProps} />);
    expect(screen.getByLabelText('Server actions')).toBeInTheDocument();
  });

  it('shows Edit, Test Connection, Disable, Delete menu items when opened', async () => {
    const user = userEvent.setup();
    render(<MCPServerRowActions {...defaultProps} />);

    await user.click(screen.getByLabelText('Server actions'));

    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Test Connection')).toBeInTheDocument();
    expect(screen.getByText('Disable')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('shows Enable label when server is disabled', async () => {
    const user = userEvent.setup();
    render(
      <MCPServerRowActions
        {...defaultProps}
        server={makeServer({ is_enabled: false, last_status: 'disabled' })}
      />
    );

    await user.click(screen.getByLabelText('Server actions'));
    expect(screen.getByText('Enable')).toBeInTheDocument();
    expect(screen.queryByText('Disable')).not.toBeInTheDocument();
  });

  it('calls onEdit with server when Edit is clicked', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const server = makeServer();
    render(<MCPServerRowActions {...defaultProps} server={server} onEdit={onEdit} />);

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Edit'));

    expect(onEdit).toHaveBeenCalledWith(server);
  });

  it('calls onTestConnection with server.id when Test Connection is clicked', async () => {
    const user = userEvent.setup();
    const onTestConnection = vi.fn();
    render(
      <MCPServerRowActions
        {...defaultProps}
        server={makeServer({ id: 'srv-42' })}
        onTestConnection={onTestConnection}
      />
    );

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Test Connection'));

    expect(onTestConnection).toHaveBeenCalledWith('srv-42');
  });

  it('calls onToggleEnabled when enable/disable is clicked', async () => {
    const user = userEvent.setup();
    const onToggleEnabled = vi.fn();
    render(
      <MCPServerRowActions
        {...defaultProps}
        server={makeServer({ id: 'srv-5', is_enabled: true })}
        onToggleEnabled={onToggleEnabled}
      />
    );

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Disable'));

    expect(onToggleEnabled).toHaveBeenCalledWith('srv-5', false);
  });

  it('shows AlertDialog when Delete is clicked', async () => {
    const user = userEvent.setup();
    render(<MCPServerRowActions {...defaultProps} server={makeServer({ display_name: 'My MCP' })} />);

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Delete'));

    expect(screen.getByText('Remove MCP Server')).toBeInTheDocument();
    expect(screen.getByText(/My MCP/)).toBeInTheDocument();
  });

  it('calls onDelete when AlertDialog confirm is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(
      <MCPServerRowActions
        {...defaultProps}
        server={makeServer({ id: 'srv-del' })}
        onDelete={onDelete}
      />
    );

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Delete'));
    await user.click(screen.getByText('Remove'));

    expect(onDelete).toHaveBeenCalledWith('srv-del');
  });

  it('does not call onDelete when AlertDialog cancel is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<MCPServerRowActions {...defaultProps} onDelete={onDelete} />);

    await user.click(screen.getByLabelText('Server actions'));
    await user.click(screen.getByText('Delete'));
    await user.click(screen.getByText('Cancel'));

    expect(onDelete).not.toHaveBeenCalled();
  });
});
