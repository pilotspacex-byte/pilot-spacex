import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPServerCard } from '../mcp-server-card';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

const makeServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'srv-1',
  workspace_id: 'ws-1',
  display_name: 'Test MCP Server',
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

describe('MCPServerCard', () => {
  it('renders server display name and URL', () => {
    render(
      <MCPServerCard
        server={makeServer()}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.getByText('Test MCP Server')).toBeInTheDocument();
    expect(screen.getByText('https://mcp.example.com')).toBeInTheDocument();
  });

  it('renders Authorize button when auth_type is oauth2 and onAuthorize is provided', () => {
    render(
      <MCPServerCard
        server={makeServer({ auth_type: 'oauth2' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        onAuthorize={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.getByText('Authorize')).toBeInTheDocument();
  });

  it('does NOT render Authorize button when auth_type is bearer', () => {
    render(
      <MCPServerCard
        server={makeServer({ auth_type: 'bearer' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        onAuthorize={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.queryByText('Authorize')).not.toBeInTheDocument();
  });

  it('calls onAuthorize with server.id when Authorize button is clicked', async () => {
    const user = userEvent.setup();
    const onAuthorize = vi.fn();

    render(
      <MCPServerCard
        server={makeServer({ id: 'srv-42', auth_type: 'oauth2' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        onAuthorize={onAuthorize}
        isDeleting={false}
      />
    );

    await user.click(screen.getByText('Authorize'));

    expect(onAuthorize).toHaveBeenCalledWith('srv-42');
  });

  it('does NOT render Authorize button when onAuthorize is undefined (backward compat)', () => {
    render(
      <MCPServerCard
        server={makeServer({ auth_type: 'oauth2' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.queryByText('Authorize')).not.toBeInTheDocument();
  });

  it('renders "None" badge when auth_type is none', () => {
    render(
      <MCPServerCard
        server={makeServer({ auth_type: 'none' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.getByText('None')).toBeInTheDocument();
  });

  it('does NOT render Authorize button when auth_type is none', () => {
    render(
      <MCPServerCard
        server={makeServer({ auth_type: 'none' })}
        onDelete={vi.fn()}
        onRefreshStatus={vi.fn()}
        onAuthorize={vi.fn()}
        isDeleting={false}
      />
    );

    expect(screen.queryByText('Authorize')).not.toBeInTheDocument();
  });
});
