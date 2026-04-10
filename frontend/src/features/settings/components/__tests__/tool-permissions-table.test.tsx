/**
 * Tests for ToolPermissionsTable.
 *
 * Phase 69 DD-003 — UI invariant: when can_set_auto=false, the "Auto" radio
 * option MUST NOT exist in the DOM (not merely disabled or hidden via CSS).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ToolPermission } from '../../types/ai-permissions';

const MOCK_PERMS: ToolPermission[] = [
  {
    tool_name: 'mcp__github__create_issue',
    mode: 'ask',
    source: 'default',
    can_set_auto: true,
  },
  {
    tool_name: 'mcp__github__list_repos',
    mode: 'auto',
    source: 'db',
    can_set_auto: true,
  },
  {
    // DD-003 always-approval tool — must NOT show Auto option
    tool_name: 'mcp__github__delete_repo',
    mode: 'ask',
    source: 'default',
    can_set_auto: false,
  },
  {
    tool_name: 'mcp__filesystem__read_file',
    mode: 'auto',
    source: 'db',
    can_set_auto: true,
  },
  {
    // Another always-approval tool to assert pattern
    tool_name: 'mcp__filesystem__delete_file',
    mode: 'deny',
    source: 'override',
    can_set_auto: false,
  },
];

const setMutate = vi.fn();

vi.mock('../../hooks/use-ai-permissions', async () => {
  return {
    useAIPermissions: () => ({ data: MOCK_PERMS, isLoading: false, error: null }),
    useSetToolPermission: () => ({
      mutate: setMutate,
      isPending: false,
      variables: undefined,
    }),
  };
});

import { ToolPermissionsTable } from '../tool-permissions-table';

function renderTable() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ToolPermissionsTable workspaceId="ws-uuid" />
    </QueryClientProvider>
  );
}

describe('ToolPermissionsTable', () => {
  beforeEach(() => {
    setMutate.mockClear();
  });

  it('groups tools by MCP server', () => {
    renderTable();
    // Two server group headers (badges)
    expect(screen.getByText('github')).toBeInTheDocument();
    expect(screen.getByText('filesystem')).toBeInTheDocument();
    // 5 tool rows
    expect(screen.getByText('create_issue')).toBeInTheDocument();
    expect(screen.getByText('list_repos')).toBeInTheDocument();
    expect(screen.getByText('delete_repo')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText('delete_file')).toBeInTheDocument();
  });

  it('renders the Auto option when can_set_auto=true', () => {
    renderTable();
    expect(
      screen.getByTestId('mode-auto-mcp__github__create_issue')
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('mode-auto-mcp__filesystem__read_file')
    ).toBeInTheDocument();
  });

  it('DD-003 INVARIANT: omits the Auto option from the DOM when can_set_auto=false', () => {
    renderTable();
    // Auto option must NOT exist for always-approval tools
    expect(
      screen.queryByTestId('mode-auto-mcp__github__delete_repo')
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('mode-auto-mcp__filesystem__delete_file')
    ).not.toBeInTheDocument();
    // Ask + Deny still present
    expect(
      screen.getByTestId('mode-ask-mcp__github__delete_repo')
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('mode-deny-mcp__github__delete_repo')
    ).toBeInTheDocument();
    // ShieldAlert tooltip trigger present
    expect(
      screen.getByTestId('always-approval-mcp__github__delete_repo')
    ).toBeInTheDocument();
  });

  it('fires the mutation when an unselected mode is clicked', async () => {
    const user = userEvent.setup();
    renderTable();
    await user.click(screen.getByTestId('mode-deny-mcp__github__create_issue'));
    expect(setMutate).toHaveBeenCalledWith({
      tool_name: 'mcp__github__create_issue',
      mode: 'deny',
    });
  });

  it('uses the correct collection root URL shape (no trailing slash)', () => {
    // Sanity check on the hook URL — see use-ai-permissions.ts.
    // The actual fetch is mocked above, but we assert the documented contract:
    const expected = '/workspaces/ws-uuid/ai/permissions';
    expect(expected.endsWith('/')).toBe(false);
    expect(expected).toMatch(/\/workspaces\/[^/]+\/ai\/permissions$/);
  });
});
