/**
 * RelatedIssuesSection component tests.
 *
 * Tests for displaying related issues with relation types and status badges.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RelatedIssuesSection } from '../related-issues-section';
import type { ContextRelatedIssue } from '@/stores/ai/AIContextStore';

describe('RelatedIssuesSection', () => {
  const mockItems: ContextRelatedIssue[] = [
    {
      relationType: 'blocks',
      issueId: 'issue-1',
      identifier: 'PS-100',
      title: 'Implement authentication system',
      summary: 'Build OAuth2 authentication with JWT tokens and refresh flow',
      status: 'In Progress',
      stateGroup: 'started',
    },
    {
      relationType: 'relates',
      issueId: 'issue-2',
      identifier: 'PS-101',
      title: 'Add user profile management',
      summary: 'Create user profile CRUD endpoints and UI components',
      status: 'Todo',
      stateGroup: 'unstarted',
    },
    {
      relationType: 'blocked_by',
      issueId: 'issue-3',
      identifier: 'PS-102',
      title: 'Setup database migrations',
      summary: 'Configure Alembic for database schema migrations',
      status: 'Done',
      stateGroup: 'completed',
    },
  ];

  it('renders nothing when items is empty', () => {
    const { container } = render(<RelatedIssuesSection items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders items with identifiers and titles', () => {
    render(<RelatedIssuesSection items={mockItems} />);

    expect(screen.getByText('PS-100')).toBeInTheDocument();
    expect(screen.getByText('Implement authentication system')).toBeInTheDocument();

    expect(screen.getByText('PS-101')).toBeInTheDocument();
    expect(screen.getByText('Add user profile management')).toBeInTheDocument();

    expect(screen.getByText('PS-102')).toBeInTheDocument();
    expect(screen.getByText('Setup database migrations')).toBeInTheDocument();
  });

  it('renders relation badges (BLOCKS, RELATES, BLOCKED BY)', () => {
    render(<RelatedIssuesSection items={mockItems} />);

    expect(screen.getByText('BLOCKS')).toBeInTheDocument();
    expect(screen.getByText('RELATES')).toBeInTheDocument();
    expect(screen.getByText('BLOCKED BY')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    render(<RelatedIssuesSection items={mockItems} />);

    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Todo')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('renders summaries with line-clamp', () => {
    render(<RelatedIssuesSection items={mockItems} />);

    expect(
      screen.getByText('Build OAuth2 authentication with JWT tokens and refresh flow')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Create user profile CRUD endpoints and UI components')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Configure Alembic for database schema migrations')
    ).toBeInTheDocument();

    const summaryElements = screen.getAllByText(
      /Build OAuth2|Create user profile|Configure Alembic/
    );
    summaryElements.forEach((element) => {
      expect(element).toHaveClass('line-clamp-2');
    });
  });
});
