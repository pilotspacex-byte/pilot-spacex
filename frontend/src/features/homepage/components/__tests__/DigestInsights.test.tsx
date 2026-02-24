/**
 * DigestInsights component tests.
 *
 * T013: Verifies category rendering, empty category hiding,
 * dismiss button, freshness indicator, loading/error/empty states.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { DigestInsights } from '../DigestInsights';
import type { DigestInsightsProps } from '../DigestInsights';
import type { DigestSuggestion } from '../../types';
import type { DigestCategoryGroup } from '../../hooks/useWorkspaceDigest';

// Mock date-fns to control freshness label
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 hours ago'),
}));

// Mock Tooltip to render children directly (avoids Radix portal issues in tests)
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipTrigger: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  TooltipContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { role: 'tooltip' }, children),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const staleSuggestion: DigestSuggestion = {
  id: 'sug-1',
  category: 'stale_issues' as const,
  title: 'PS-42 has been idle for 14 days',
  description: 'Consider closing or reassigning.',
  entityId: 'entity-1',
  entityType: 'issue',
  entityIdentifier: 'PS-42',
  projectId: 'proj-1',
  projectName: 'Test Project',
  actionType: 'navigate',
  actionLabel: 'View',
  actionUrl: '/issues/entity-1',
  relevanceScore: 0.9,
};

const unlinkedSuggestion: DigestSuggestion = {
  id: 'sug-2',
  category: 'unlinked_notes' as const,
  title: 'Meeting notes contain actionable items',
  description: 'Extract issues from meeting notes.',
  entityId: 'entity-2',
  entityType: 'note',
  entityIdentifier: null,
  projectId: null,
  projectName: null,
  actionType: 'navigate',
  actionLabel: 'Review',
  actionUrl: '/notes/entity-2',
  relevanceScore: 0.7,
};

const mockGroups: DigestCategoryGroup[] = [
  { category: 'stale_issues', items: [staleSuggestion] },
  { category: 'unlinked_notes', items: [unlinkedSuggestion] },
];

const defaultProps: DigestInsightsProps = {
  groups: mockGroups,
  generatedAt: '2026-02-20T08:00:00Z',
  isLoading: false,
  isError: false,
  isRefreshing: false,
  onDismiss: vi.fn(),
  onRefresh: vi.fn(),
  onRetry: vi.fn(),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DigestInsights', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders category cards with correct labels and counts', () => {
    render(React.createElement(DigestInsights, defaultProps));

    const staleRegion = screen.getByRole('region', { name: /stale issues/i });
    expect(staleRegion).toBeDefined();
    expect(within(staleRegion).getByText('Stale Issues')).toBeDefined();
    expect(within(staleRegion).getByText('1')).toBeDefined();

    const unlinkedRegion = screen.getByRole('region', { name: /unlinked notes/i });
    expect(unlinkedRegion).toBeDefined();
    expect(within(unlinkedRegion).getByText('Unlinked Notes')).toBeDefined();
  });

  it('renders suggestion titles within category cards', () => {
    render(React.createElement(DigestInsights, defaultProps));

    expect(screen.getByText('PS-42 has been idle for 14 days')).toBeDefined();
    expect(screen.getByText('Meeting notes contain actionable items')).toBeDefined();
  });

  it('renders entity identifier badges', () => {
    render(React.createElement(DigestInsights, defaultProps));

    expect(screen.getByText('PS-42')).toBeDefined();
  });

  it('hides empty categories (FR-004)', () => {
    const propsWithEmpty: DigestInsightsProps = {
      ...defaultProps,
      groups: [{ category: 'stale_issues', items: [staleSuggestion] }],
    };

    render(React.createElement(DigestInsights, propsWithEmpty));

    expect(screen.queryByText('Unlinked Notes')).toBeNull();
    expect(screen.queryByText('Blocked')).toBeNull();
  });

  it('displays freshness timestamp', () => {
    render(React.createElement(DigestInsights, defaultProps));

    expect(screen.getByText('Updated 2 hours ago')).toBeDefined();
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();

    render(React.createElement(DigestInsights, { ...defaultProps, onDismiss }));

    const dismissButtons = screen.getAllByRole('button', { name: /dismiss/i });
    expect(dismissButtons.length).toBeGreaterThan(0);

    await user.click(dismissButtons[0]!);

    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledWith(staleSuggestion);
  });

  it('calls onRefresh when refresh button is clicked', async () => {
    const onRefresh = vi.fn();
    const user = userEvent.setup();

    render(React.createElement(DigestInsights, { ...defaultProps, onRefresh }));

    const refreshBtn = screen.getByRole('button', { name: /refresh digest/i });
    await user.click(refreshBtn);

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(React.createElement(DigestInsights, { ...defaultProps, isLoading: true }));

    expect(screen.getByLabelText('Loading insights')).toBeDefined();
    expect(screen.queryByText('Stale Issues')).toBeNull();
  });

  it('shows error state with retry button when isError is true', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();

    render(React.createElement(DigestInsights, { ...defaultProps, isError: true, onRetry }));

    expect(screen.getByText('Failed to load insights.')).toBeDefined();

    const retryBtn = screen.getByRole('button', { name: /retry/i });
    await user.click(retryBtn);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when no groups are available', () => {
    render(React.createElement(DigestInsights, { ...defaultProps, groups: [] }));

    expect(screen.getByText('No suggestions right now.')).toBeDefined();
    expect(screen.getByText('AI insights will appear as your workspace grows.')).toBeDefined();
  });

  it('disables refresh button when isRefreshing is true', () => {
    render(React.createElement(DigestInsights, { ...defaultProps, isRefreshing: true }));

    const refreshBtn = screen.getByRole('button', { name: /refresh digest/i });
    expect(refreshBtn).toHaveProperty('disabled', true);
    expect(screen.getByText('Refreshing...')).toBeDefined();
  });
});
