/**
 * Tests for MCPServerDialog - Phase 25 modal dialog component.
 *
 * Verifies: tab defaults (Import JSON on add, Form Config on edit),
 * Cancel closes dialog, Test Connection button presence.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MCPServerDialog } from '../mcp-server-dialog';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

const makeServer = (overrides?: Partial<MCPServer>): MCPServer => ({
  id: 'srv-1',
  workspace_id: 'ws-1',
  display_name: 'Edit Server',
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
  open: true,
  onOpenChange: vi.fn(),
  onSave: vi.fn().mockResolvedValue(undefined),
  onImport: vi.fn().mockResolvedValue(undefined),
  isSaving: false,
};

describe('MCPServerDialog', () => {
  it('shows "Add New MCP Server" title in add mode', () => {
    render(<MCPServerDialog {...defaultProps} />);
    expect(screen.getByText('Add New MCP Server')).toBeInTheDocument();
  });

  it('shows "Edit MCP Server" title in edit mode', () => {
    render(<MCPServerDialog {...defaultProps} initialData={makeServer()} />);
    expect(screen.getByText('Edit MCP Server')).toBeInTheDocument();
  });

  it('shows Import JSON tab in add mode', () => {
    render(<MCPServerDialog {...defaultProps} />);
    expect(screen.getByText('Import JSON')).toBeInTheDocument();
    expect(screen.getByText('Form Configuration')).toBeInTheDocument();
  });

  it('hides Import JSON tab in edit mode', () => {
    render(<MCPServerDialog {...defaultProps} initialData={makeServer()} />);
    expect(screen.queryByText('Import JSON')).not.toBeInTheDocument();
    expect(screen.getByText('Form Configuration')).toBeInTheDocument();
  });

  it('shows Test Connection button in edit mode when onTestConnection is provided', () => {
    render(
      <MCPServerDialog
        {...defaultProps}
        initialData={makeServer()}
        onTestConnection={vi.fn().mockResolvedValue({ status: 'enabled', latency_ms: 42 })}
      />
    );

    // Need to switch to Form Configuration tab content
    expect(screen.getByText('Test Connection')).toBeInTheDocument();
  });

  it('does NOT show Test Connection button in add mode', () => {
    render(<MCPServerDialog {...defaultProps} />);
    expect(screen.queryByText('Test Connection')).not.toBeInTheDocument();
  });

  it('calls onOpenChange(false) when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <MCPServerDialog
        {...defaultProps}
        initialData={makeServer()}
        onOpenChange={onOpenChange}
      />
    );

    await user.click(screen.getByText('Cancel'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows "Save Changes" button in edit mode', () => {
    render(<MCPServerDialog {...defaultProps} initialData={makeServer()} />);
    expect(screen.getByText('Save Changes')).toBeInTheDocument();
  });

  it('does not render dialog content when open is false', () => {
    render(<MCPServerDialog {...defaultProps} open={false} />);
    expect(screen.queryByText('Add New MCP Server')).not.toBeInTheDocument();
  });
});
