/**
 * code-page.test.tsx — Route-level smoke test for the Code page.
 *
 * Verifies:
 * 1. Code page renders without crash
 * 2. Renders the EditorLayout wrapper container
 * 3. Dynamic imports are properly mocked for SSR-incompatible modules
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock Next.js navigation
vi.mock('next/navigation', () => ({
  useParams: () => ({
    workspaceSlug: 'test-workspace',
    projectId: 'test-project-id',
  }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Mock next/dynamic — return a synchronous stub component
vi.mock('next/dynamic', () => ({
  default: (_importFn: () => Promise<unknown>, opts?: { loading?: () => React.ReactNode }) => {
    // Return a synchronous component that just renders a test div
    return function DynamicStub(props: Record<string, unknown>) {
      // Use loading fallback if provided during loading state
      if (opts?.loading) {
        return opts.loading() as React.ReactElement;
      }
      return React.createElement('div', { 'data-testid': 'editor-layout-stub', ...props });
    };
  },
}));

// Mock stores
vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: {
      currentWorkspace: { id: 'workspace-123' },
    },
  }),
}));

// Mock artifacts hook
vi.mock('@/features/artifacts/hooks', () => ({
  useProjectArtifacts: (_workspaceId: string, _projectId: string) => ({
    data: [],
    isLoading: false,
    error: null,
  }),
}));

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

import CodePage from '@/app/(workspace)/[workspaceSlug]/projects/[projectId]/code/page';

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('Code Page', () => {
  it('renders without crash', () => {
    expect(() => renderWithQueryClient(<CodePage />)).not.toThrow();
  });

  it('renders the code page container', () => {
    renderWithQueryClient(<CodePage />);
    // The page renders a container div with data-testid
    expect(screen.getByTestId('code-page')).toBeDefined();
  });

  it('renders EditorLayout (or loading state) inside the container', () => {
    renderWithQueryClient(<CodePage />);
    const container = screen.getByTestId('code-page');
    expect(container).toBeDefined();
    // Should have children (either skeleton or editor layout stub)
    expect(container.children.length).toBeGreaterThan(0);
  });
});
