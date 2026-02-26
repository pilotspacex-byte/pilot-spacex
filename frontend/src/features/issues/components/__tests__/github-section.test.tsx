/**
 * GitHubSection component tests.
 *
 * Verifies empty state, PR list, commit list, section header count,
 * conditional rendering, and loading skeleton display.
 */

import { render, screen, within, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { GitHubSection } from '../github-section';
import type { IntegrationLink } from '@/types';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createPRLink(overrides?: Partial<IntegrationLink>): IntegrationLink {
  return {
    id: 'pr-1',
    issueId: 'issue-1',
    integrationType: 'github_pr',
    externalId: '42',
    externalUrl: 'https://github.com/org/repo/pull/42',
    link_type: 'pull_request',
    prNumber: 42,
    prTitle: 'Fix auth bug',
    prStatus: 'open',
    ...overrides,
  };
}

function createCommitLink(overrides?: Partial<IntegrationLink>): IntegrationLink {
  return {
    id: 'commit-1',
    issueId: 'issue-1',
    integrationType: 'github_issue',
    externalId: 'abc1234',
    externalUrl: 'https://github.com/org/repo/commit/abc1234',
    link_type: 'commit',
    title: 'feat: add user auth',
    authorName: 'Alice',
    ...overrides,
  };
}

/** Opens the GitHub CollapsibleSection by clicking its trigger button. */
function openSection() {
  fireEvent.click(screen.getByRole('button', { name: /github/i }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GitHubSection', () => {
  it('renders empty state when no PRs and no commits', () => {
    render(<GitHubSection pullRequests={[]} commits={[]} />);
    openSection();

    expect(screen.getByText('No linked GitHub activity')).toBeInTheDocument();
  });

  it('renders GitHub section title', () => {
    render(<GitHubSection pullRequests={[]} commits={[]} />);

    expect(screen.getByText('GitHub')).toBeInTheDocument();
  });

  it('renders PR list when pullRequests provided', () => {
    const prs = [
      createPRLink({ id: 'pr-1', prNumber: 1, prTitle: 'First PR' }),
      createPRLink({ id: 'pr-2', prNumber: 2, prTitle: 'Second PR' }),
    ];

    // defaultOpen=true since total > 0, no click needed
    render(<GitHubSection pullRequests={prs} commits={[]} />);

    expect(screen.getByText('First PR')).toBeInTheDocument();
    expect(screen.getByText('Second PR')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('renders commit list when commits provided', () => {
    const commits = [
      createCommitLink({ id: 'c-1', title: 'feat: add login' }),
      createCommitLink({ id: 'c-2', title: 'fix: null pointer' }),
    ];

    render(<GitHubSection pullRequests={[]} commits={commits} />);

    expect(screen.getByText('feat: add login')).toBeInTheDocument();
    expect(screen.getByText('fix: null pointer')).toBeInTheDocument();
  });

  it('shows correct total count in section header badge', () => {
    const prs = [createPRLink({ id: 'pr-1' }), createPRLink({ id: 'pr-2' })];
    const commits = [
      createCommitLink({ id: 'c-1' }),
      createCommitLink({ id: 'c-2' }),
      createCommitLink({ id: 'c-3' }),
    ];

    render(<GitHubSection pullRequests={prs} commits={commits} />);

    // CollapsibleSection renders count badge with total = 5
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('does not render PR section when pullRequests is empty', () => {
    const commits = [createCommitLink({ id: 'c-1', title: 'fix: resolve crash' })];

    render(<GitHubSection pullRequests={[]} commits={commits} />);

    expect(screen.queryByText('Pull Requests')).not.toBeInTheDocument();
    expect(screen.getByText('Recent Commits')).toBeInTheDocument();
    expect(screen.getByText('fix: resolve crash')).toBeInTheDocument();
  });

  it('does not render commit section when commits is empty', () => {
    const prs = [createPRLink({ id: 'pr-1', prTitle: 'Only PR' })];

    render(<GitHubSection pullRequests={prs} commits={[]} />);

    expect(screen.queryByText('Recent Commits')).not.toBeInTheDocument();
    expect(screen.getByText('Pull Requests')).toBeInTheDocument();
    expect(screen.getByText('Only PR')).toBeInTheDocument();
  });

  it('renders loading skeleton rows when isLoading is true', () => {
    // Provide non-empty arrays so defaultOpen=true and content is in DOM
    render(<GitHubSection pullRequests={[createPRLink()]} commits={[]} isLoading={true} />);

    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('does not render PR or commit content when isLoading is true', () => {
    render(
      <GitHubSection
        pullRequests={[createPRLink({ prTitle: 'My PR' })]}
        commits={[]}
        isLoading={true}
      />
    );

    expect(screen.queryByText('My PR')).not.toBeInTheDocument();
  });

  it('renders PR status badge with correct capitalization', () => {
    render(<GitHubSection pullRequests={[createPRLink({ prStatus: 'merged' })]} commits={[]} />);

    expect(screen.getByText('Merged')).toBeInTheDocument();
  });

  it('PR links have correct href, target, and rel attributes', () => {
    const url = 'https://github.com/org/repo/pull/99';
    render(<GitHubSection pullRequests={[createPRLink({ externalUrl: url })]} commits={[]} />);

    const list = screen.getByRole('list', { name: 'Linked pull requests' });
    const link = within(list).getByRole('link');
    expect(link).toHaveAttribute('href', url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('commit links have correct href, target, and rel attributes', () => {
    const url = 'https://github.com/org/repo/commit/abc1234';
    render(<GitHubSection pullRequests={[]} commits={[createCommitLink({ externalUrl: url })]} />);

    const list = screen.getByRole('list', { name: 'Linked commits' });
    const link = within(list).getByRole('link');
    expect(link).toHaveAttribute('href', url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders author name for commits', () => {
    render(
      <GitHubSection pullRequests={[]} commits={[createCommitLink({ authorName: 'Bob Smith' })]} />
    );

    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
  });

  it('renders separator between PRs and commits when both present', () => {
    const { container } = render(
      <GitHubSection
        pullRequests={[createPRLink({ id: 'pr-1' })]}
        commits={[createCommitLink({ id: 'c-1' })]}
      />
    );

    const separator = container.querySelector('hr');
    expect(separator).toBeTruthy();
  });
});
