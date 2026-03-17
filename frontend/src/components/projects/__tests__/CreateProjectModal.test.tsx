/**
 * CreateProjectModal component tests.
 *
 * Verifies auto-generation of identifier from name, submit button state,
 * and form reset when modal closes.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CreateProjectModal } from '../CreateProjectModal';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();

vi.mock('@/features/projects/hooks', () => ({
  useCreateProject: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
}));

vi.mock('@/features/issues/hooks/use-workspace-members', () => ({
  useWorkspaceMembers: vi.fn(() => ({ data: [], isLoading: false })),
}));

import { useCreateProject } from '@/features/projects/hooks';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CreateProjectModal', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    workspaceId: 'ws-1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useCreateProject).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateProject>);
  });

  it('renders modal with title "Create Project"', () => {
    render(<CreateProjectModal {...defaultProps} />);
    expect(screen.getByRole('heading', { name: 'Create Project' })).toBeInTheDocument();
  });

  it('renders name input field', () => {
    render(<CreateProjectModal {...defaultProps} />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
  });

  it('renders identifier input field', () => {
    render(<CreateProjectModal {...defaultProps} />);
    expect(screen.getByLabelText(/identifier/i)).toBeInTheDocument();
  });

  it('renders description textarea', () => {
    render(<CreateProjectModal {...defaultProps} />);
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  it('auto-generates identifier from project name', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'Authentication Service');

    const identifierInput = screen.getByLabelText(/identifier/i) as HTMLInputElement;
    expect(identifierInput.value).toBe('AS');
  });

  it('auto-generates identifier from single word name with at least 2 chars', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'Backend');

    const identifierInput = screen.getByLabelText(/identifier/i) as HTMLInputElement;
    expect(identifierInput.value).toBe('BAC');
  });

  it('disables submit when identifier is less than 2 characters', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    const identifierInput = screen.getByLabelText(/identifier/i);
    await user.type(screen.getByLabelText(/name/i), 'Test');
    await user.clear(identifierInput);
    await user.type(identifierInput, 'A');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    expect(submitButton).toBeDisabled();
  });

  it('stops auto-generating identifier after manual edit', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    const nameInput = screen.getByLabelText(/name/i);
    const identifierInput = screen.getByLabelText(/identifier/i);

    // Type name first
    await user.type(nameInput, 'My Project');
    expect((identifierInput as HTMLInputElement).value).toBe('MP');

    // Manually edit identifier (maxLength=5, so "CUST" fits within limit)
    await user.clear(identifierInput);
    await user.type(identifierInput, 'CUST');

    // Now type more in name - identifier should not change
    await user.clear(nameInput);
    await user.type(nameInput, 'New Name');
    expect((identifierInput as HTMLInputElement).value).toBe('CUST');
  });

  it('uppercases and strips non-alphanumeric from identifier input', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    const identifierInput = screen.getByLabelText(/identifier/i);
    await user.type(identifierInput, 'ab-1');

    expect((identifierInput as HTMLInputElement).value).toBe('AB1');
  });

  it('submit button is disabled when name is empty', () => {
    render(<CreateProjectModal {...defaultProps} />);
    const submitButton = screen.getByRole('button', { name: /create project/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is enabled when name and identifier are filled', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    await user.type(screen.getByLabelText(/name/i), 'My Project');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('calls mutate with correct data on submit', async () => {
    const user = userEvent.setup();
    render(<CreateProjectModal {...defaultProps} />);

    await user.type(screen.getByLabelText(/name/i), 'Auth Service');
    await user.type(screen.getByLabelText(/description/i), 'Handles auth');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    expect(mockMutate).toHaveBeenCalledWith({
      name: 'Auth Service',
      identifier: 'AS',
      description: 'Handles auth',
      icon: undefined,
    });
  });

  it('resets form when modal closes', async () => {
    const { rerender } = render(<CreateProjectModal {...defaultProps} />);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/name/i), 'Test Project');

    // Close modal by setting open to false
    rerender(<CreateProjectModal {...defaultProps} open={false} />);

    // Reopen modal
    rerender(<CreateProjectModal {...defaultProps} open={true} />);

    const nameInput = screen.getByLabelText(/name/i) as HTMLInputElement;
    expect(nameInput.value).toBe('');

    const identifierInput = screen.getByLabelText(/identifier/i) as HTMLInputElement;
    expect(identifierInput.value).toBe('');
  });

  it('shows "Creating..." text when mutation is pending', () => {
    vi.mocked(useCreateProject).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    } as unknown as ReturnType<typeof useCreateProject>);

    render(<CreateProjectModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /creating/i })).toBeInTheDocument();
  });

  it('disables cancel button when mutation is pending', () => {
    vi.mocked(useCreateProject).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    } as unknown as ReturnType<typeof useCreateProject>);

    render(<CreateProjectModal {...defaultProps} />);
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    expect(cancelButton).toBeDisabled();
  });

  it('calls onOpenChange(false) when cancel is clicked', async () => {
    const onOpenChange = vi.fn();
    const user = userEvent.setup();

    render(<CreateProjectModal {...defaultProps} onOpenChange={onOpenChange} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
