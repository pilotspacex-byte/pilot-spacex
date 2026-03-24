/**
 * Tests for FormConfigTab - Phase 25 form configuration component.
 *
 * Verifies: required field validation, transport auto-sets on type change,
 * command args visibility, secret masking, submit payload, header/env visibility.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormConfigTab } from '../form-config-tab';
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
  has_auth_secret: true,
  has_headers: false,
  has_headers_encrypted: false,
  has_env_secret: false,
  is_enabled: true,
  last_status: 'enabled',
  last_status_checked_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('FormConfigTab', () => {
  it('renders Server Name and Server Type fields', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);

    expect(screen.getByLabelText('Server Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Server Type')).toBeInTheDocument();
  });

  it('renders URL label as "Server URL" for remote type', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.getByLabelText('Server URL')).toBeInTheDocument();
  });

  it('renders Headers and Environment Variables sections', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.getByText('Headers')).toBeInTheDocument();
    expect(screen.getByText('Environment Variables')).toBeInTheDocument();
  });

  it('does NOT show Command Arguments for remote type', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.queryByLabelText('Command Arguments')).not.toBeInTheDocument();
  });

  it('shows secret mask text when editing server with has_auth_secret=true', () => {
    render(
      <FormConfigTab
        initialData={makeServer({ has_auth_secret: true })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.getByText(/Leave blank to keep existing token/)).toBeInTheDocument();
  });

  it('pre-populates headers when editing server with existing headers', () => {
    render(
      <FormConfigTab
        initialData={makeServer({
          headers: { 'X-Custom': 'value1', 'Authorization': 'Bearer xyz' },
          has_headers: true,
        })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.getByDisplayValue('X-Custom')).toBeInTheDocument();
    expect(screen.getByDisplayValue('value1')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Authorization')).toBeInTheDocument();
  });

  it('pre-populates env var keys with masked values when editing', () => {
    render(
      <FormConfigTab
        initialData={makeServer({
          env_var_keys: ['API_KEY', 'SECRET_TOKEN'],
          has_env_secret: true,
        })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.getByDisplayValue('API_KEY')).toBeInTheDocument();
    expect(screen.getByDisplayValue('SECRET_TOKEN')).toBeInTheDocument();
    expect(screen.getByText(/Existing variables shown with hidden values/)).toBeInTheDocument();
  });

  it('shows Authentication section for remote type', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.getByText('Authentication')).toBeInTheDocument();
    expect(screen.getByText('None')).toBeInTheDocument();
    expect(screen.getByText('Bearer Token')).toBeInTheDocument();
    expect(screen.getByText('OAuth 2.0')).toBeInTheDocument();
  });

  it('renders Add Header and Add Variable buttons', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.getByText('Add Header')).toBeInTheDocument();
    expect(screen.getByText('Add Variable')).toBeInTheDocument();
  });

  it('calls onSave with correct payload when form is submitted', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'My Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');

    // Submit the form
    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload.display_name).toBe('My Server');
    expect(payload.url_or_command).toBe('https://example.com/sse');
    expect(payload.server_type).toBe('remote');
    expect(payload.transport).toBe('sse');
  });

  it('populates form fields from initialData in edit mode', () => {
    render(
      <FormConfigTab
        initialData={makeServer({ display_name: 'Pre-filled', url_or_command: 'https://pre.com' })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );

    expect(screen.getByDisplayValue('Pre-filled')).toBeInTheDocument();
    expect(screen.getByDisplayValue('https://pre.com')).toBeInTheDocument();
  });

  it('disables all inputs when isSaving is true', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={true} />);
    expect(screen.getByLabelText('Server Name')).toBeDisabled();
  });

  it('renders None radio option in Authentication section', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.getByText('None')).toBeInTheDocument();
  });

  it('defaults to None auth type for new servers', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    const noneRadio = screen.getByDisplayValue('none') as HTMLInputElement;
    expect(noneRadio.checked).toBe(true);
  });

  it('hides Bearer Token input field when None auth is selected', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    // Default is none, so the password input for the token should not be visible
    expect(screen.queryByPlaceholderText('Token (encrypted server-side)')).not.toBeInTheDocument();
  });

  it('submits auth_type as none when None is selected', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'No Auth Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload.auth_type).toBe('none');
  });

  it('does not include unchanged env vars in submit payload', async () => {
    const onSave = vi.fn();
    render(
      <FormConfigTab
        initialData={makeServer({
          env_var_keys: ['API_KEY'],
          has_env_secret: true,
        })}
        onSave={onSave}
        isSaving={false}
      />
    );

    // Submit without changing the env var value (which is empty/masked)
    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    // Empty-valued env vars should not be sent (preserves existing encrypted values)
    expect(payload.env_vars).toBeUndefined();
  });

  it('shows Command Runner selector when server type is command', () => {
    render(
      <FormConfigTab
        initialData={makeServer({ server_type: 'command', command_runner: 'npx', transport: 'stdio', auth_type: 'none' })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );

    expect(screen.getByLabelText('Command Runner')).toBeInTheDocument();
  });

  it('does NOT show Command Runner selector for remote type', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);
    expect(screen.queryByLabelText('Command Runner')).not.toBeInTheDocument();
  });

  it('includes command_runner in submit payload for command type servers', async () => {
    const onSave = vi.fn();
    render(
      <FormConfigTab
        initialData={makeServer({
          server_type: 'command',
          command_runner: 'uvx',
          transport: 'stdio',
          url_or_command: 'mcp-server-git',
          auth_type: 'none',
        })}
        onSave={onSave}
        isSaving={false}
      />
    );

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload.command_runner).toBe('uvx');
    expect(payload.server_type).toBe('command');
  });

  it('sends command_runner as null for remote type in edit mode', async () => {
    const onSave = vi.fn();
    render(
      <FormConfigTab
        initialData={makeServer({ server_type: 'remote', command_runner: null })}
        onSave={onSave}
        isSaving={false}
      />
    );

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload.command_runner).toBeNull();
  });

  it('does NOT show Package/Command input for command type servers', () => {
    render(
      <FormConfigTab
        initialData={makeServer({ server_type: 'command', command_runner: 'npx', transport: 'stdio', auth_type: 'none' })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.queryByLabelText('Package / Command')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Server URL')).not.toBeInTheDocument();
  });

  it('pre-populates Command Arguments from url_or_command for command servers in edit mode', () => {
    render(
      <FormConfigTab
        initialData={makeServer({
          server_type: 'command',
          command_runner: 'uvx',
          transport: 'stdio',
          url_or_command: 'mcp-server-git',
          auth_type: 'none',
        })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.getByDisplayValue('mcp-server-git')).toBeInTheDocument();
  });

  it('sends url_or_command from commandArgs field for command servers', async () => {
    const onSave = vi.fn();
    render(
      <FormConfigTab
        initialData={makeServer({
          server_type: 'command',
          command_runner: 'npx',
          transport: 'stdio',
          url_or_command: '@foo/bar',
          auth_type: 'none',
        })}
        onSave={onSave}
        isSaving={false}
      />
    );

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const payload = onSave.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload.url_or_command).toBe('@foo/bar');
    expect(payload.command_runner).toBe('npx');
    expect(payload.command_args).toBeNull();
  });

  it('shows full command preview note after args input for command servers', () => {
    render(
      <FormConfigTab
        initialData={makeServer({
          server_type: 'command',
          command_runner: 'npx',
          transport: 'stdio',
          url_or_command: '@foo/bar',
          auth_type: 'none',
        })}
        onSave={vi.fn()}
        isSaving={false}
      />
    );
    expect(screen.getByText(/Full command:/)).toBeInTheDocument();
  });

  it('shows URL validation error and blocks submit for invalid remote URL', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'Invalid URL Server');
    await user.type(screen.getByLabelText('Server URL'), 'not-a-url');

    expect(screen.getByText('Please enter a valid URL (must include https://)')).toBeInTheDocument();

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).not.toHaveBeenCalled();
  });

  it('accepts valid remote URL and allows submit', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'Valid URL Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');

    expect(screen.queryByText('Please enter a valid URL (must include https://)')).not.toBeInTheDocument();

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('blocks submit when authType is oauth2 and required OAuth fields are empty', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'OAuth Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');
    await user.click(screen.getByLabelText('OAuth 2.0'));

    expect(screen.getByText('Client ID is required')).toBeInTheDocument();
    expect(screen.getByText('Authorization URL is required')).toBeInTheDocument();
    expect(screen.getByText('Token URL is required')).toBeInTheDocument();

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).not.toHaveBeenCalled();
  });

  it('blocks submit when authType is oauth2 and only client ID is provided', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'OAuth Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');
    await user.click(screen.getByLabelText('OAuth 2.0'));
    await user.type(screen.getByLabelText('Client ID'), 'client-123');

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).not.toHaveBeenCalled();
  });

  it('allows submit when authType is oauth2 and required fields are present', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<FormConfigTab onSave={onSave} isSaving={false} />);

    await user.type(screen.getByLabelText('Server Name'), 'OAuth Server');
    await user.type(screen.getByLabelText('Server URL'), 'https://example.com/sse');
    await user.click(screen.getByLabelText('OAuth 2.0'));
    await user.type(screen.getByLabelText('Client ID'), 'client-123');
    await user.type(screen.getByLabelText('Authorization URL'), 'https://provider.com/oauth/authorize');
    await user.type(screen.getByLabelText('Token URL'), 'https://provider.com/oauth/token');

    const form = screen.getByLabelText('Server Name').closest('form')!;
    form.dispatchEvent(new Event('submit', { bubbles: true }));

    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('renders auth radios inside a fieldset with legend Authentication', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);

    expect(screen.getByRole('group', { name: 'Authentication' })).toBeInTheDocument();
  });

  it('renders indexed aria-labels for KV editor inputs', async () => {
    const user = userEvent.setup();
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);

    await user.click(screen.getByText('Add Header'));
    await user.click(screen.getByText('Add Variable'));

    expect(screen.getByLabelText('Headers key 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Headers value 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Environment Variables key 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Environment Variables value 1')).toBeInTheDocument();
  });

  it('renders keyboard-focusable tooltip help triggers', () => {
    render(<FormConfigTab onSave={vi.fn()} isSaving={false} />);

    expect(screen.getByRole('button', { name: 'Headers help' })).toHaveAttribute('tabIndex', '0');
    expect(screen.getByRole('button', { name: 'Environment variables help' })).toHaveAttribute('tabIndex', '0');
  });
});
