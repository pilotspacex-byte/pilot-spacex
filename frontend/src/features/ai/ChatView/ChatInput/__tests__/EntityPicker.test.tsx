import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// cmdk requires scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock hooks — EntityPicker tests should test UI behavior, not hook logic
vi.mock('../../hooks/useEntitySearch', () => ({
  useEntitySearch: vi.fn().mockReturnValue({
    notes: [],
    issues: [],
    projects: [],
    isLoading: false,
  }),
}));

import { useEntitySearch } from '../../hooks/useEntitySearch';
import { EntityPicker } from '../EntityPicker';
import type { RecentEntity } from '../../hooks/useRecentEntities';

const mockOnSelect = vi.fn();
const mockOnOpenChange = vi.fn();

function entity(id: string, type: RecentEntity['type'], title: string): RecentEntity {
  return { id, type, title };
}

const sampleRecent: RecentEntity[] = [
  entity('r1', 'Note', 'Recent Note'),
  entity('r2', 'Issue', 'Recent Bug'),
];

function renderPicker(overrides: Partial<React.ComponentProps<typeof EntityPicker>> = {}) {
  return render(
    <EntityPicker
      open={true}
      onOpenChange={mockOnOpenChange}
      query=""
      workspaceId="ws-1"
      recentEntities={[]}
      onSelect={mockOnSelect}
      width={400}
      {...overrides}
    />
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useEntitySearch).mockReturnValue({
    notes: [],
    issues: [],
    projects: [],
    isLoading: false,
  });
});

describe('EntityPicker', () => {
  it('does not render content when closed', () => {
    renderPicker({ open: false });
    expect(screen.queryByText('Recent')).not.toBeInTheDocument();
  });

  it('shows recent entities zone when query is empty and recents exist', () => {
    renderPicker({ recentEntities: sampleRecent });
    expect(screen.getByText('Recent')).toBeInTheDocument();
    expect(screen.getByText('Recent Note')).toBeInTheDocument();
    expect(screen.getByText('Recent Bug')).toBeInTheDocument();
  });

  it('hides recent entities zone when query is non-empty (FR-02-10)', () => {
    renderPicker({ recentEntities: sampleRecent, query: 'search' });
    expect(screen.queryByText('Recent')).not.toBeInTheDocument();
  });

  it('renders Notes group when notes are available', () => {
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [{ id: 'n1', title: 'Design Doc' }] as never[],
      issues: [],
      projects: [],
      isLoading: false,
    });
    renderPicker();
    expect(screen.getByText('Notes')).toBeInTheDocument();
    expect(screen.getByText('Design Doc')).toBeInTheDocument();
  });

  it('renders Issues group with issue.name (not deprecated issue.title)', () => {
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [],
      issues: [{ id: 'i1', name: 'Fix login bug', identifier: 'PS-42' }] as never[],
      projects: [],
      isLoading: false,
    });
    renderPicker();
    expect(screen.getByText('Issues')).toBeInTheDocument();
    expect(screen.getByText('Fix login bug')).toBeInTheDocument();
  });

  it('renders Projects group with project.name', () => {
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [],
      issues: [],
      projects: [{ id: 'p1', name: 'Frontend App' }] as never[],
      isLoading: false,
    });
    renderPicker();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Frontend App')).toBeInTheDocument();
  });

  it('hides groups with zero results (FR-02-6)', () => {
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [{ id: 'n1', title: 'A Note' }] as never[],
      issues: [],
      projects: [],
      isLoading: false,
    });
    renderPicker();
    expect(screen.getByText('Notes')).toBeInTheDocument();
    expect(screen.queryByText('Issues')).not.toBeInTheDocument();
    expect(screen.queryByText('Projects')).not.toBeInTheDocument();
  });

  it('shows empty state when all groups are empty and no recents', () => {
    renderPicker({ recentEntities: [], query: 'zzzzz' });
    expect(screen.getByText('No results for "zzzzz"')).toBeInTheDocument();
  });

  it('calls onSelect with RecentEntity when a note item is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [{ id: 'n1', title: 'My Note' }] as never[],
      issues: [],
      projects: [],
      isLoading: false,
    });
    renderPicker();

    await user.click(screen.getByText('My Note'));

    expect(mockOnSelect).toHaveBeenCalledWith({
      id: 'n1',
      type: 'Note',
      title: 'My Note',
    });
  });

  it('calls onSelect with issue.name as title when an issue item is clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(useEntitySearch).mockReturnValue({
      notes: [],
      issues: [{ id: 'i1', name: 'Bug Report' }] as never[],
      projects: [],
      isLoading: false,
    });
    renderPicker();

    await user.click(screen.getByText('Bug Report'));

    expect(mockOnSelect).toHaveBeenCalledWith({
      id: 'i1',
      type: 'Issue',
      title: 'Bug Report',
    });
  });

  it('calls onSelect when a recent entity is clicked', async () => {
    const user = userEvent.setup();
    renderPicker({ recentEntities: sampleRecent });

    await user.click(screen.getByText('Recent Note'));

    expect(mockOnSelect).toHaveBeenCalledWith(sampleRecent[0]);
  });

  it('passes query and workspaceId to useEntitySearch', () => {
    renderPicker({ query: 'test', workspaceId: 'ws-abc' });
    expect(useEntitySearch).toHaveBeenCalledWith({
      query: 'test',
      workspaceId: 'ws-abc',
    });
  });
});

