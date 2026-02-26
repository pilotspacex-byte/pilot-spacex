/**
 * ActivityEntry component tests (T038).
 *
 * Verifies comment, state_changed, assigned, created activities,
 * actor avatar, "System" fallback, relative time formatting,
 * and timeline connector visibility.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ActivityEntry } from '../activity-entry';
import type { Activity } from '@/types';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createActivity(overrides?: Partial<Activity>): Activity {
  return {
    id: 'act-1',
    activityType: 'comment_added',
    field: null,
    oldValue: null,
    newValue: null,
    comment: 'This is a comment',
    metadata: null,
    createdAt: new Date().toISOString(),
    actor: { id: 'user-1', email: 'john@test.com', displayName: 'John Doe' },
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ActivityEntry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders comment activity with comment text', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'comment_added',
          comment: 'Great work on this feature!',
        })}
      />
    );

    expect(screen.getByText('Great work on this feature!')).toBeInTheDocument();
  });

  it('renders state_changed activity with old/new values', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'updated',
          field: 'state',
          oldValue: 'Todo',
          newValue: 'In Progress',
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/changed state from Todo to In Progress/)).toBeInTheDocument();
  });

  it('renders assigned activity', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'updated',
          field: 'assignee',
          newValue: 'Jane Smith',
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/assigned to Jane Smith/)).toBeInTheDocument();
  });

  it('renders created activity', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'created',
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/created this issue/)).toBeInTheDocument();
  });

  it('shows actor avatar with first letter', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          actor: { id: 'u1', email: 'alice@test.com', displayName: 'Alice' },
        })}
      />
    );

    // Avatar should show 'A' for Alice
    const avatars = screen.getAllByText('A');
    expect(avatars.length).toBeGreaterThanOrEqual(1);
  });

  it('shows "System" for null actor', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'created',
          actor: null,
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/System created this issue/)).toBeInTheDocument();
  });

  it('shows actor name from displayName', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'comment_added',
          actor: { id: 'u1', email: 'john@test.com', displayName: 'John Doe' },
        })}
      />
    );

    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('falls back to email when displayName is null', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'comment_added',
          actor: { id: 'u1', email: 'john@test.com', displayName: null },
        })}
      />
    );

    expect(screen.getByText('john@test.com')).toBeInTheDocument();
  });

  it('relative time formatting - just now', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          createdAt: '2025-06-15T12:00:00Z',
        })}
      />
    );

    expect(screen.getByText('just now')).toBeInTheDocument();
  });

  it('relative time formatting - minutes ago', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          createdAt: '2025-06-15T11:45:00Z',
        })}
      />
    );

    expect(screen.getByText('15m ago')).toBeInTheDocument();
  });

  it('relative time formatting - hours ago', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          createdAt: '2025-06-15T09:00:00Z',
        })}
      />
    );

    expect(screen.getByText('3h ago')).toBeInTheDocument();
  });

  it('timeline connector visible when not last entry', () => {
    const { container } = render(<ActivityEntry activity={createActivity()} isLast={false} />);

    // The connector is a div with absolute positioning and bg-border class
    const connector = container.querySelector('.bg-border');
    expect(connector).toBeTruthy();
  });

  it('timeline connector hidden when isLast=true', () => {
    const { container } = render(<ActivityEntry activity={createActivity()} isLast={true} />);

    // No connector should be present
    const connector = container.querySelector('.bg-border');
    expect(connector).toBeNull();
  });

  it('renders removed assignee text', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'updated',
          field: 'assignee',
          newValue: null,
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/removed assignee/)).toBeInTheDocument();
  });

  it('renders priority change', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'updated',
          field: 'priority',
          oldValue: 'low',
          newValue: 'high',
          comment: null,
        })}
      />
    );

    expect(screen.getByText(/changed priority from low to high/)).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // GitHub integration activity handlers
  // ---------------------------------------------------------------------------

  it('renders commit_linked activity with short SHA and message', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: 'abc12345',
          comment: null,
          metadata: {
            link_type: 'commit',
            sha: 'abc12345def67890',
            commit_message: 'feat: add user auth',
            repository: 'org/repo',
          },
        })}
      />
    );

    expect(screen.getByText('abc12345')).toBeInTheDocument();
    expect(screen.getByText(/feat: add user auth/)).toBeInTheDocument();
  });

  it('renders commit_linked with external link when external_url provided', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: 'abc12345',
          comment: null,
          metadata: {
            link_type: 'commit',
            sha: 'abc12345def67890',
            commit_message: 'fix: resolve null pointer',
            external_url: 'https://github.com/org/repo/commit/abc12345def67890',
          },
        })}
      />
    );

    const link = screen.getByRole('link', { name: /View commit abc12345 on GitHub/i });
    expect(link).toHaveAttribute('href', 'https://github.com/org/repo/commit/abc12345def67890');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders commit_linked truncates long messages at 60 chars', () => {
    const longMessage = 'a'.repeat(70);
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: 'abc12345',
          comment: null,
          metadata: {
            link_type: 'commit',
            sha: 'abc12345def67890',
            commit_message: longMessage,
          },
        })}
      />
    );

    expect(screen.getByText(new RegExp(`${'a'.repeat(60)}…`))).toBeInTheDocument();
  });

  it('renders pr_linked (open) with PR number, title, and open badge', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: '#42',
          comment: null,
          metadata: {
            link_type: 'pull_request',
            pr_title: 'Add feature X',
            state: 'open',
          },
        })}
      />
    );

    expect(screen.getByText(/PR #42/)).toBeInTheDocument();
    expect(screen.getByText(/Add feature X/)).toBeInTheDocument();
    expect(screen.getByText('open')).toBeInTheDocument();
  });

  it('renders pr_linked (merged) with merged badge', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: '#99',
          comment: null,
          metadata: {
            link_type: 'pull_request',
            pr_title: 'Merge feature Y',
            state: 'merged',
          },
        })}
      />
    );

    expect(screen.getByText(/PR #99/)).toBeInTheDocument();
    expect(screen.getByText('merged')).toBeInTheDocument();
  });

  it('renders pr_linked (closed) with closed badge', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: '#7',
          comment: null,
          metadata: {
            link_type: 'pull_request',
            pr_title: 'Draft work',
            state: 'closed',
          },
        })}
      />
    );

    expect(screen.getByText(/PR #7/)).toBeInTheDocument();
    expect(screen.getByText('closed')).toBeInTheDocument();
  });

  it('renders pr_linked with external link when external_url provided', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'linked_to_note',
          field: 'integration_link',
          newValue: '#55',
          comment: null,
          metadata: {
            link_type: 'pull_request',
            pr_title: 'Fix login',
            state: 'open',
            external_url: 'https://github.com/org/repo/pull/55',
          },
        })}
      />
    );

    const link = screen.getByRole('link', { name: /View PR #55 on GitHub/i });
    expect(link).toHaveAttribute('href', 'https://github.com/org/repo/pull/55');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders auto-transition state_changed with PR annotation', () => {
    render(
      <ActivityEntry
        activity={createActivity({
          activityType: 'state_changed',
          field: 'state',
          oldValue: 'In Progress',
          newValue: 'Done',
          comment: null,
          metadata: {
            auto_transition: true,
            trigger: 'pr_merged',
            pr_number: 42,
          },
        })}
      />
    );

    expect(screen.getByText(/changed state from In Progress to Done/)).toBeInTheDocument();
    expect(screen.getByText(/auto · PR #42/)).toBeInTheDocument();
  });
});
