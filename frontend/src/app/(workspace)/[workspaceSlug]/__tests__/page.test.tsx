/**
 * Tests for app/(workspace)/[workspaceSlug]/page.tsx — BUG-01
 *
 * Covers:
 * - WorkspaceHomePage reads workspaceId from WorkspaceContext (workspace.id), NOT from slug string
 * - workspaceId is UUID even when workspaceStore.currentWorkspace is null
 */

import React from 'react';
import { render, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Mock useWorkspace — returns workspace with UUID id
// Store is intentionally null to test that context is the source of truth
const mockUseWorkspace = vi.fn();

vi.mock('@/components/workspace-guard', () => ({
  useWorkspace: () => mockUseWorkspace(),
}));

// Mock workspaceStore — currentWorkspace is null to reproduce the bug scenario
vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: vi.fn().mockReturnValue({
    currentWorkspace: null,
  }),
}));

// Capture props passed to OnboardingChecklist
const mockOnboardingChecklistProps = vi.fn();

vi.mock('@/features/onboarding', () => ({
  OnboardingChecklist: (props: Record<string, unknown>) => {
    mockOnboardingChecklistProps(props);
    return (
      <div data-testid="onboarding-checklist" data-workspace-id={props.workspaceId as string} />
    );
  },
}));

vi.mock('@/features/homepage', () => ({
  HomepageHub: () => <div data-testid="homepage-hub" />,
}));

vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

// ---------------------------------------------------------------------------
// Import page component (after mocks)
// ---------------------------------------------------------------------------

import WorkspaceHomePage from '../page';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('WorkspaceHomePage — BUG-01: workspaceId source', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset useWorkspace to default: context has UUID, store has null
    mockUseWorkspace.mockReturnValue({
      workspace: { id: 'uuid-abc', name: 'Test WS', slug: 'test' },
      workspaceSlug: 'test',
    });
  });

  it('passes workspace.id UUID from context to OnboardingChecklist, not the slug string', async () => {
    await act(async () => {
      render(<WorkspaceHomePage params={Promise.resolve({ workspaceSlug: 'test' })} />);
      // Wait for the Promise-based params to resolve through React.use()
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(mockOnboardingChecklistProps).toHaveBeenCalledWith(
      expect.objectContaining({
        workspaceId: 'uuid-abc',
      })
    );

    // Explicitly assert it is NOT the slug string
    expect(mockOnboardingChecklistProps).not.toHaveBeenCalledWith(
      expect.objectContaining({
        workspaceId: 'test',
      })
    );
  });

  it('uses UUID from WorkspaceContext even when workspaceStore.currentWorkspace is null', async () => {
    // workspaceStore mock already returns null for currentWorkspace
    await act(async () => {
      render(<WorkspaceHomePage params={Promise.resolve({ workspaceSlug: 'test' })} />);
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    const callArg = mockOnboardingChecklistProps.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(callArg).toBeDefined();
    expect(callArg.workspaceId).toBe('uuid-abc');
    // Should NOT be the slug
    expect(callArg.workspaceId).not.toBe('test');
  });
});
