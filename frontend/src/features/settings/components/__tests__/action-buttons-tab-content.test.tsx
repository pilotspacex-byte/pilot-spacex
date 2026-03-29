/**
 * ActionButtonsTabContent tests — SKBTN-01, SKBTN-02
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActionButtonsTabContent } from '../action-buttons-tab-content';
import type { SkillActionButton } from '@/services/api/skill-action-buttons';

// Mock TanStack hooks
const mockAdminButtons: SkillActionButton[] = [
  {
    id: 'btn-1',
    name: 'Generate Tests',
    icon: 'Zap',
    binding_type: 'skill',
    binding_id: 'skill-1',
    binding_metadata: { skill_name: 'test-generator' },
    sort_order: 0,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'btn-2',
    name: 'Review Code',
    icon: null,
    binding_type: 'mcp_tool',
    binding_id: null,
    binding_metadata: { tool_name: 'code-review' },
    sort_order: 1,
    is_active: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockMutate = vi.fn();
const mockUpdateMutate = vi.fn();
const mockDeleteMutate = vi.fn();

vi.mock('@/services/api/skill-action-buttons', () => ({
  useAdminActionButtons: vi.fn(() => ({
    data: mockAdminButtons,
    isLoading: false,
  })),
  useCreateActionButton: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
  useUpdateActionButton: vi.fn(() => ({
    mutate: mockUpdateMutate,
    isPending: false,
  })),
  useReorderActionButtons: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useDeleteActionButton: vi.fn(() => ({
    mutate: mockDeleteMutate,
    isPending: false,
  })),
  ACTION_BUTTONS_KEY: 'action-buttons',
}));

vi.mock('@/services/api/skill-templates', () => ({
  useSkillTemplates: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('ActionButtonsTabContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders list of action buttons', () => {
    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    expect(screen.getByText('Generate Tests')).toBeInTheDocument();
    expect(screen.getByText('Review Code')).toBeInTheDocument();
  });

  it('shows binding type badge for each button', () => {
    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    expect(screen.getByText('Skill')).toBeInTheDocument();
    expect(screen.getByText('MCP Tool')).toBeInTheDocument();
  });

  it('shows inactive badge for disabled buttons', () => {
    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('renders Add Button button', () => {
    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    expect(screen.getByRole('button', { name: /add button/i })).toBeInTheDocument();
  });

  it('shows empty state when no buttons', async () => {
    const { useAdminActionButtons } = await import('@/services/api/skill-action-buttons');
    (useAdminActionButtons as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
    });

    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    expect(screen.getByText(/no action buttons configured/i)).toBeInTheDocument();
  });

  it('calls update mutation when toggling active state', async () => {
    const user = userEvent.setup();
    // Reset mock to use original data
    const { useAdminActionButtons } = await import('@/services/api/skill-action-buttons');
    (useAdminActionButtons as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockAdminButtons,
      isLoading: false,
    });

    render(<ActionButtonsTabContent workspaceId="ws-123" />);

    // Find the toggle switches - the active button's toggle
    const switches = screen.getAllByRole('switch');
    expect(switches.length).toBeGreaterThan(0);

    await user.click(switches[0]!);

    expect(mockUpdateMutate).toHaveBeenCalledWith(
      { buttonId: 'btn-1', data: { is_active: false } },
      expect.any(Object)
    );
  });
});
