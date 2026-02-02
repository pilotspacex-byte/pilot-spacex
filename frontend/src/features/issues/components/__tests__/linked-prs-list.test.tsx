/**
 * LinkedPRsList component tests (T025).
 *
 * Verifies empty state, github_pr filtering, PR number/title/status,
 * status colors, external link attributes, and URL rendering.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LinkedPRsList } from '../linked-prs-list';
import type { IntegrationLink } from '@/types';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createPRLink(overrides?: Partial<IntegrationLink>): IntegrationLink {
  return {
    id: 'link-1',
    issueId: 'issue-1',
    integrationType: 'github_pr',
    externalId: '123',
    externalUrl: 'https://github.com/org/repo/pull/123',
    prNumber: 123,
    prTitle: 'Fix authentication bug',
    prStatus: 'open',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LinkedPRsList', () => {
  it('renders empty state when no links', () => {
    render(<LinkedPRsList links={[]} />);
    expect(screen.getByText('No linked pull requests')).toBeInTheDocument();
  });

  it('renders empty state when links exist but none are github_pr type', () => {
    const links: IntegrationLink[] = [
      {
        id: 'link-1',
        issueId: 'issue-1',
        integrationType: 'slack',
        externalId: 'C123',
        externalUrl: 'https://slack.com/channel/123',
      },
    ];

    render(<LinkedPRsList links={links} />);
    expect(screen.getByText('No linked pull requests')).toBeInTheDocument();
  });

  it('filters to only github_pr type links', () => {
    const links: IntegrationLink[] = [
      createPRLink({ id: 'pr-1', prTitle: 'PR One' }),
      {
        id: 'slack-1',
        issueId: 'issue-1',
        integrationType: 'slack',
        externalId: 'C123',
        externalUrl: 'https://slack.com',
      },
      createPRLink({ id: 'pr-2', prTitle: 'PR Two' }),
    ];

    render(<LinkedPRsList links={links} />);

    const list = screen.getByRole('list', { name: 'Linked pull requests' });
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(2);
  });

  it('shows PR number, title, and status badge', () => {
    render(<LinkedPRsList links={[createPRLink()]} />);

    expect(screen.getByText('#123')).toBeInTheDocument();
    expect(screen.getByText('Fix authentication bug')).toBeInTheDocument();
    expect(screen.getByText('Open')).toBeInTheDocument();
  });

  it('shows externalId when prTitle is not provided', () => {
    render(<LinkedPRsList links={[createPRLink({ prTitle: undefined, externalId: 'ext-456' })]} />);

    expect(screen.getByText('ext-456')).toBeInTheDocument();
  });

  it('does not show PR number when prNumber is not provided', () => {
    render(<LinkedPRsList links={[createPRLink({ prNumber: undefined })]} />);

    expect(screen.queryByText(/#\d+/)).not.toBeInTheDocument();
  });

  it('status badge has blue classes for Open', () => {
    render(<LinkedPRsList links={[createPRLink({ prStatus: 'open' })]} />);

    const badge = screen.getByText('Open');
    expect(badge.className).toContain('bg-blue-100');
    expect(badge.className).toContain('text-blue-700');
  });

  it('status badge has purple classes for Merged', () => {
    render(<LinkedPRsList links={[createPRLink({ prStatus: 'merged' })]} />);

    const badge = screen.getByText('Merged');
    expect(badge.className).toContain('bg-purple-100');
    expect(badge.className).toContain('text-purple-700');
  });

  it('status badge has gray classes for Closed', () => {
    render(<LinkedPRsList links={[createPRLink({ prStatus: 'closed' })]} />);

    const badge = screen.getByText('Closed');
    expect(badge.className).toContain('bg-gray-100');
    expect(badge.className).toContain('text-gray-600');
  });

  it('links have target="_blank" and rel="noopener noreferrer"', () => {
    render(<LinkedPRsList links={[createPRLink()]} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders external URL correctly', () => {
    const url = 'https://github.com/org/repo/pull/456';
    render(<LinkedPRsList links={[createPRLink({ externalUrl: url })]} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', url);
  });

  it('renders multiple PRs', () => {
    const links = [
      createPRLink({ id: 'pr-1', prNumber: 1, prTitle: 'First PR' }),
      createPRLink({ id: 'pr-2', prNumber: 2, prTitle: 'Second PR' }),
      createPRLink({ id: 'pr-3', prNumber: 3, prTitle: 'Third PR' }),
    ];

    render(<LinkedPRsList links={links} />);

    const list = screen.getByRole('list');
    const items = within(list).getAllByRole('listitem');
    expect(items).toHaveLength(3);
  });

  // -------------------------------------------------------------------------
  // Navigation (T041)
  // -------------------------------------------------------------------------

  describe('Navigation (T041)', () => {
    it('all PR links have target="_blank" attribute', () => {
      const links = [
        createPRLink({ id: 'pr-1', externalUrl: 'https://github.com/org/repo/pull/1' }),
        createPRLink({ id: 'pr-2', externalUrl: 'https://github.com/org/repo/pull/2' }),
      ];

      render(<LinkedPRsList links={links} />);

      const allLinks = screen.getAllByRole('link');
      for (const link of allLinks) {
        expect(link).toHaveAttribute('target', '_blank');
      }
    });

    it('all PR links have rel="noopener noreferrer" attribute', () => {
      const links = [createPRLink({ id: 'pr-1' }), createPRLink({ id: 'pr-2' })];

      render(<LinkedPRsList links={links} />);

      const allLinks = screen.getAllByRole('link');
      for (const link of allLinks) {
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      }
    });

    it('PR links point to correct external URLs', () => {
      const links = [
        createPRLink({
          id: 'pr-1',
          externalUrl: 'https://github.com/org/repo/pull/101',
        }),
        createPRLink({
          id: 'pr-2',
          externalUrl: 'https://github.com/org/repo/pull/202',
        }),
      ];

      render(<LinkedPRsList links={links} />);

      const allLinks = screen.getAllByRole('link');
      expect(allLinks[0]).toHaveAttribute('href', 'https://github.com/org/repo/pull/101');
      expect(allLinks[1]).toHaveAttribute('href', 'https://github.com/org/repo/pull/202');
    });

    it('Open status badge has blue styling', () => {
      render(<LinkedPRsList links={[createPRLink({ prStatus: 'open' })]} />);

      const badge = screen.getByText('Open');
      expect(badge.className).toContain('bg-blue-100');
      expect(badge.className).toContain('text-blue-700');
    });

    it('Merged status badge has purple styling', () => {
      render(<LinkedPRsList links={[createPRLink({ prStatus: 'merged' })]} />);

      const badge = screen.getByText('Merged');
      expect(badge.className).toContain('bg-purple-100');
      expect(badge.className).toContain('text-purple-700');
    });

    it('Closed status badge has gray styling', () => {
      render(<LinkedPRsList links={[createPRLink({ prStatus: 'closed' })]} />);

      const badge = screen.getByText('Closed');
      expect(badge.className).toContain('bg-gray-100');
      expect(badge.className).toContain('text-gray-600');
    });
  });
});
