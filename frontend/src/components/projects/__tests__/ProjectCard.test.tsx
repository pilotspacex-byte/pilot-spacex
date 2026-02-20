/**
 * ProjectCard component tests.
 *
 * Verifies rendering of project details, grid/list variants,
 * keyboard accessibility, and lead avatar display.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProjectCard } from '../ProjectCard';
import type { Project } from '@/types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
      const { initial, animate, transition, ...domProps } = props;
      return <div {...domProps}>{children}</div>;
    },
  },
}));

const mockProject: Project = {
  id: 'proj-1',
  name: 'Test Project',
  description: 'A test project',
  identifier: 'TP',
  workspaceId: 'ws-1',
  leadId: 'user-1',
  lead: { id: 'user-1', email: 'lead@test.com', displayName: 'Lead User' },
  icon: '🚀',
  issueCount: 10,
  openIssueCount: 3,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
};

// ---------------------------------------------------------------------------
// Tests - Grid variant (default)
// ---------------------------------------------------------------------------

describe('ProjectCard - grid variant', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders project name', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('renders project identifier', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText('TP')).toBeInTheDocument();
  });

  it('renders project description', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText('A test project')).toBeInTheDocument();
  });

  it('renders progress as completed/total issues', () => {
    render(<ProjectCard project={mockProject} />);
    // 10 total - 3 open = 7 completed
    expect(screen.getByText('7/10 issues')).toBeInTheDocument();
  });

  it('renders project icon when provided', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText('🚀')).toBeInTheDocument();
  });

  it('renders lead avatar initials when lead is present', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.getByText('LU')).toBeInTheDocument();
  });

  it('does not render lead avatar when lead is absent', () => {
    const projectWithoutLead = { ...mockProject, lead: undefined, leadId: undefined };
    render(<ProjectCard project={projectWithoutLead} />);
    expect(screen.queryByText('LU')).not.toBeInTheDocument();
  });

  it('shows "No description" when description is empty', () => {
    const projectNoDesc = { ...mockProject, description: undefined };
    render(<ProjectCard project={projectNoDesc} />);
    expect(screen.getByText('No description')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} onClick={onClick} />);
    fireEvent.click(screen.getByText('Test Project'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('has button role and aria-label when onClick is provided', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} onClick={onClick} />);
    const button = screen.getByRole('button', { name: 'Open project Test Project' });
    expect(button).toBeInTheDocument();
  });

  it('triggers onClick on Enter key press', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} onClick={onClick} />);
    const button = screen.getByRole('button', { name: 'Open project Test Project' });
    fireEvent.keyDown(button, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('triggers onClick on Space key press', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} onClick={onClick} />);
    const button = screen.getByRole('button', { name: 'Open project Test Project' });
    fireEvent.keyDown(button, { key: ' ' });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not add button role when onClick is not provided', () => {
    render(<ProjectCard project={mockProject} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders 0/0 issues for project with no issues', () => {
    const emptyProject = { ...mockProject, issueCount: 0, openIssueCount: 0 };
    render(<ProjectCard project={emptyProject} />);
    expect(screen.getByText('0/0 issues')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Tests - List variant
// ---------------------------------------------------------------------------

describe('ProjectCard - list variant', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders project name in list variant', () => {
    render(<ProjectCard project={mockProject} variant="list" />);
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('renders project identifier in list variant', () => {
    render(<ProjectCard project={mockProject} variant="list" />);
    expect(screen.getByText('TP')).toBeInTheDocument();
  });

  it('renders progress count in list variant', () => {
    render(<ProjectCard project={mockProject} variant="list" />);
    expect(screen.getByText('7/10')).toBeInTheDocument();
  });

  it('renders lead avatar in list variant when lead is present', () => {
    render(<ProjectCard project={mockProject} variant="list" />);
    expect(screen.getByText('LU')).toBeInTheDocument();
  });

  it('calls onClick in list variant', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} variant="list" onClick={onClick} />);
    fireEvent.click(screen.getByText('Test Project'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('keyboard accessible in list variant', () => {
    const onClick = vi.fn();
    render(<ProjectCard project={mockProject} variant="list" onClick={onClick} />);
    const button = screen.getByRole('button', { name: 'Open project Test Project' });
    fireEvent.keyDown(button, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders project icon in list variant', () => {
    render(<ProjectCard project={mockProject} variant="list" />);
    expect(screen.getByText('🚀')).toBeInTheDocument();
  });
});
