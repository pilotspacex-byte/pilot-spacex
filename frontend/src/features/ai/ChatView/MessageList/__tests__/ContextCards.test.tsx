/**
 * Unit tests for ContextNotesResultCard and ContextIssuesResultCard.
 *
 * Tests:
 * - ContextNotesResultCard: shows heading, empty state, renders NotePreviewCard per note
 * - ContextIssuesResultCard: shows heading, empty state, renders IssueReferenceCard per issue
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('@/features/issues/components/note-preview-card', () => ({
  NotePreviewCard: ({ noteTitle }: { noteTitle: string }) => (
    <div data-testid="note-preview">{noteTitle}</div>
  ),
}));

vi.mock('@/features/issues/components/issue-reference-card', () => ({
  IssueReferenceCard: ({ title }: { title: string }) => (
    <div data-testid="issue-reference">{title}</div>
  ),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

import { ContextNotesResultCard, ContextIssuesResultCard } from '../ContextCards';

describe('ContextNotesResultCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "Related Notes" heading', () => {
    render(<ContextNotesResultCard data={{ notes: [] }} />);
    expect(screen.getByText('Related Notes')).toBeInTheDocument();
  });

  it('renders "No related notes found" when data.notes is empty', () => {
    render(<ContextNotesResultCard data={{ notes: [] }} />);
    expect(screen.getByText('No related notes found')).toBeInTheDocument();
  });

  it('renders "No related notes found" when data.notes is absent', () => {
    render(<ContextNotesResultCard data={{}} />);
    expect(screen.getByText('No related notes found')).toBeInTheDocument();
  });

  it('renders NotePreviewCard for each note in data.notes', () => {
    const notes = [
      { noteId: 'n1', noteTitle: 'Note Alpha', linkType: 'CREATED', workspaceSlug: 'ws' },
      { noteId: 'n2', noteTitle: 'Note Beta', linkType: 'EXTRACTED', workspaceSlug: 'ws' },
      { noteId: 'n3', noteTitle: 'Note Gamma', linkType: 'REFERENCED', workspaceSlug: 'ws' },
    ];

    render(<ContextNotesResultCard data={{ notes }} />);

    const cards = screen.getAllByTestId('note-preview');
    expect(cards).toHaveLength(3);
    expect(screen.getByText('Note Alpha')).toBeInTheDocument();
    expect(screen.getByText('Note Beta')).toBeInTheDocument();
    expect(screen.getByText('Note Gamma')).toBeInTheDocument();
  });

  it('does not show empty state when notes are present', () => {
    const notes = [
      { noteId: 'n1', noteTitle: 'Note Alpha', linkType: 'CREATED', workspaceSlug: 'ws' },
    ];

    render(<ContextNotesResultCard data={{ notes }} />);
    expect(screen.queryByText('No related notes found')).not.toBeInTheDocument();
  });
});

describe('ContextIssuesResultCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "Related Issues" heading', () => {
    render(<ContextIssuesResultCard data={{ issues: [] }} />);
    expect(screen.getByText('Related Issues')).toBeInTheDocument();
  });

  it('renders "No related issues found" when data.issues is empty', () => {
    render(<ContextIssuesResultCard data={{ issues: [] }} />);
    expect(screen.getByText('No related issues found')).toBeInTheDocument();
  });

  it('renders "No related issues found" when data.issues is absent', () => {
    render(<ContextIssuesResultCard data={{}} />);
    expect(screen.getByText('No related issues found')).toBeInTheDocument();
  });

  it('renders IssueReferenceCard for each issue in data.issues', () => {
    const issues = [
      {
        issueId: 'i1',
        identifier: 'PS-1',
        title: 'First issue',
        stateGroup: 'unstarted',
        relationType: 'blocks',
        workspaceSlug: 'ws',
      },
      {
        issueId: 'i2',
        identifier: 'PS-2',
        title: 'Second issue',
        stateGroup: 'started',
        relationType: 'relates',
        workspaceSlug: 'ws',
      },
    ];

    render(<ContextIssuesResultCard data={{ issues }} />);

    const cards = screen.getAllByTestId('issue-reference');
    expect(cards).toHaveLength(2);
    expect(screen.getByText('First issue')).toBeInTheDocument();
    expect(screen.getByText('Second issue')).toBeInTheDocument();
  });

  it('does not show empty state when issues are present', () => {
    const issues = [
      {
        issueId: 'i1',
        identifier: 'PS-1',
        title: 'First issue',
        stateGroup: 'unstarted',
        relationType: 'blocks',
        workspaceSlug: 'ws',
      },
    ];

    render(<ContextIssuesResultCard data={{ issues }} />);
    expect(screen.queryByText('No related issues found')).not.toBeInTheDocument();
  });
});
