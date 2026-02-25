/**
 * Unit tests for IssueReferenceCard component.
 *
 * Tests:
 * - Renders identifier in monospace span
 * - Renders title text
 * - Has role="button" and tabIndex=0
 * - Navigates to issue on click via router.push
 * - Navigates to issue on Enter keydown
 * - Shows relationType label: blocks, blocked by, relates
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

const mockPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

import { IssueReferenceCard } from '../issue-reference-card';

const BASE_PROPS = {
  issueId: 'issue-001',
  identifier: 'PS-42',
  title: 'Fix login bug',
  stateGroup: 'unstarted',
  relationType: 'blocks' as const,
  workspaceSlug: 'my-workspace',
};

describe('IssueReferenceCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders identifier in a monospace span', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    expect(screen.getByText('PS-42')).toBeInTheDocument();
  });

  it('renders the title text', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    expect(screen.getByText('Fix login bug')).toBeInTheDocument();
  });

  it('has role="button" and tabIndex=0', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    const card = screen.getByRole('button');
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute('tabindex', '0');
  });

  it('calls router.push with correct path on click', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    fireEvent.click(screen.getByRole('button'));
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/issues/issue-001');
  });

  it('calls router.push on Enter keydown', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' });
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/issues/issue-001');
  });

  it('calls router.push on Space keydown', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: ' ' });
    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith('/my-workspace/issues/issue-001');
  });

  it('does not call router.push on other keydown (e.g. Escape)', () => {
    render(<IssueReferenceCard {...BASE_PROPS} />);
    fireEvent.keyDown(screen.getByRole('button'), { key: 'Escape' });
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('shows "blocks" label for relationType blocks', () => {
    render(<IssueReferenceCard {...BASE_PROPS} relationType="blocks" />);
    expect(screen.getByText('blocks')).toBeInTheDocument();
  });

  it('shows "blocked by" label for relationType blocked_by', () => {
    render(<IssueReferenceCard {...BASE_PROPS} relationType="blocked_by" />);
    expect(screen.getByText('blocked by')).toBeInTheDocument();
  });

  it('shows "relates" label for relationType relates', () => {
    render(<IssueReferenceCard {...BASE_PROPS} relationType="relates" />);
    expect(screen.getByText('relates')).toBeInTheDocument();
  });

  it('uses workspaceSlug and issueId in the pushed path', () => {
    render(
      <IssueReferenceCard
        issueId="issue-xyz"
        identifier="PS-99"
        title="Another issue"
        stateGroup="started"
        relationType="relates"
        workspaceSlug="other-slug"
      />
    );
    fireEvent.click(screen.getByRole('button'));
    expect(mockPush).toHaveBeenCalledWith('/other-slug/issues/issue-xyz');
  });
});
