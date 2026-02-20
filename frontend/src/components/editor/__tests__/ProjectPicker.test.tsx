/**
 * Unit tests for ProjectPicker component.
 *
 * Tests the searchable project combobox including:
 * - Trigger rendering (with/without current project)
 * - Dropdown with project list
 * - Selection and mutation calls
 * - Remove project action
 * - Accessibility (ARIA attributes)
 *
 * @module components/editor/__tests__/ProjectPicker.test
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ProjectPicker } from '../ProjectPicker';
import type { Project } from '@/types';

// Mock TanStack Query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(),
}));

// Mock Popover to render inline (no portal)
vi.mock('@/components/ui/popover', () => ({
  Popover: ({
    children,
    open,
    onOpenChange,
  }: {
    children: React.ReactNode;
    open?: boolean;
    onOpenChange?: (v: boolean) => void;
  }) => (
    <div data-open={open} data-onchange={!!onOpenChange}>
      {children}
    </div>
  ),
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PopoverContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="popover-content" className={className}>
      {children}
    </div>
  ),
}));

// Mock Command components to simple divs for testing
vi.mock('@/components/ui/command', () => ({
  Command: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CommandInput: ({ placeholder, ...props }: { placeholder?: string; [k: string]: unknown }) => (
    <input placeholder={placeholder} data-testid="command-input" {...props} />
  ),
  CommandList: ({ children, id }: { children: React.ReactNode; id?: string }) => (
    <div data-testid="command-list" id={id}>
      {children}
    </div>
  ),
  CommandEmpty: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="command-empty">{children}</div>
  ),
  CommandGroup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CommandItem: ({
    children,
    onSelect,
    value,
    ...props
  }: {
    children: React.ReactNode;
    onSelect?: () => void;
    value?: string;
    [k: string]: unknown;
  }) => (
    <div role="option" aria-selected={false} onClick={onSelect} data-value={value} {...props}>
      {children}
    </div>
  ),
  CommandSeparator: () => <hr />,
}));

// Mock API clients
vi.mock('@/services/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}));

vi.mock('@/services/api/notes', () => ({
  notesApi: { update: vi.fn() },
}));

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Auth Project',
    description: 'Authentication module',
    identifier: 'AUTH',
    slug: 'auth-project',
    workspaceId: 'ws-1',
    memberIds: [],
    issueCount: 12,
    openIssueCount: 7,
    completedIssueCount: 5,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

const mockProjects: Project[] = [
  makeProject({ id: 'proj-1', name: 'Auth Project', issueCount: 12, completedIssueCount: 5 }),
  makeProject({
    id: 'proj-2',
    name: 'Dashboard',
    slug: 'dashboard',
    issueCount: 8,
    completedIssueCount: 8,
  }),
  makeProject({
    id: 'proj-3',
    name: 'Settings',
    slug: 'settings',
    issueCount: 4,
    completedIssueCount: 1,
  }),
];

const mockMutate = vi.fn();
const mockCancelQueries = vi.fn();
const mockInvalidateQueries = vi.fn();

describe('ProjectPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (useQueryClient as Mock).mockReturnValue({
      cancelQueries: mockCancelQueries,
      invalidateQueries: mockInvalidateQueries,
      getQueryData: vi.fn().mockReturnValue(undefined),
      setQueryData: vi.fn(),
    });

    (useQuery as Mock).mockReturnValue({
      data: { items: mockProjects, total: 3, page: 1, pageSize: 50, hasMore: false },
      isLoading: false,
    });

    (useMutation as Mock).mockImplementation(
      ({ onMutate }: { onMutate?: (v: unknown) => void }) => ({
        mutate: (projectId: string | null) => {
          mockMutate(projectId);
          onMutate?.(projectId);
        },
        isPending: false,
      })
    );
  });

  it('renders trigger with "Add project..." when no current project', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    const trigger = screen.getByTestId('project-picker-trigger');
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveTextContent('Add project...');
    expect(trigger).toHaveAttribute('aria-label', 'Add project');
  });

  it('renders trigger with project name when currentProjectId matches', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" currentProjectId="proj-1" />);

    const trigger = screen.getByTestId('project-picker-trigger');
    expect(trigger).toHaveTextContent('Auth Project');
    expect(trigger).toHaveAttribute('aria-label', 'Project: Auth Project');
  });

  it('renders all projects in the dropdown', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    expect(screen.getByText('Auth Project')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows issue progress for each project', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    expect(screen.getByText('5 of 12 issues done')).toBeInTheDocument();
    expect(screen.getByText('8 of 8 issues done')).toBeInTheDocument();
    expect(screen.getByText('1 of 4 issues done')).toBeInTheDocument();
  });

  it('calls mutation with project ID when a project is selected', async () => {
    const user = userEvent.setup();
    const onProjectChange = vi.fn();

    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" onProjectChange={onProjectChange} />);

    const dashboardItem = screen.getByTestId('project-picker-item-proj-2');
    await user.click(dashboardItem);

    expect(mockMutate).toHaveBeenCalledWith('proj-2');
    expect(onProjectChange).toHaveBeenCalledWith('proj-2');
  });

  it('does not mutate when selecting the already-selected project', async () => {
    const user = userEvent.setup();

    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" currentProjectId="proj-1" />);

    const authItem = screen.getByTestId('project-picker-item-proj-1');
    await user.click(authItem);

    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('shows check icon on the currently selected project', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" currentProjectId="proj-2" />);

    // proj-2 item should have a check icon (svg child)
    const dashboardItem = screen.getByTestId('project-picker-item-proj-2');
    const svgs = dashboardItem.querySelectorAll('svg');
    // Should have at least one SVG (the Check icon) beyond the color dot
    expect(svgs.length).toBeGreaterThan(0);

    // proj-1 should not have a check
    const authItem = screen.getByTestId('project-picker-item-proj-1');
    const authSvgs = authItem.querySelectorAll('svg');
    expect(authSvgs.length).toBe(0);
  });

  it('shows "Remove project" option when a project is selected', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" currentProjectId="proj-1" />);

    expect(screen.getByTestId('project-picker-remove')).toBeInTheDocument();
    expect(screen.getByText('Remove project')).toBeInTheDocument();
  });

  it('does not show "Remove project" when no project is selected', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    expect(screen.queryByTestId('project-picker-remove')).not.toBeInTheDocument();
  });

  it('calls mutation with null when "Remove project" is clicked', async () => {
    const user = userEvent.setup();
    const onProjectChange = vi.fn();

    render(
      <ProjectPicker
        workspaceId="ws-1"
        noteId="note-1"
        currentProjectId="proj-1"
        onProjectChange={onProjectChange}
      />
    );

    const removeBtn = screen.getByTestId('project-picker-remove');
    await user.click(removeBtn);

    expect(mockMutate).toHaveBeenCalledWith(null);
    expect(onProjectChange).toHaveBeenCalledWith(null);
  });

  it('has correct ARIA attributes on trigger', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    const trigger = screen.getByTestId('project-picker-trigger');
    expect(trigger).toHaveAttribute('role', 'combobox');
    expect(trigger).toHaveAttribute('aria-expanded');
    expect(trigger).toHaveAttribute('aria-controls', 'project-picker-list');
  });

  it('renders search input with correct placeholder', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    expect(screen.getByPlaceholderText('Search projects...')).toBeInTheDocument();
  });

  it('renders empty state when no projects available', () => {
    (useQuery as Mock).mockReturnValue({
      data: { items: [], total: 0, page: 1, pageSize: 50, hasMore: false },
      isLoading: false,
    });

    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    expect(screen.getByText('No projects found.')).toBeInTheDocument();
  });

  it('renders "Add project..." with italic styling when no project selected', () => {
    render(<ProjectPicker workspaceId="ws-1" noteId="note-1" />);

    const addText = screen.getByText('Add project...');
    expect(addText.className).toContain('italic');
    expect(addText.className).toContain('opacity-60');
  });
});
