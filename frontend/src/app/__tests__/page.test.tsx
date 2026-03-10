/**
 * Tests for app/page.tsx — auto-workspace creation (ONBD-01 / BUG-02)
 *
 * Covers:
 * - Auto-creates workspace from email prefix when user has no workspaces
 * - Retries with new suffix on 409 slug collision
 * - Falls back to manual form on second 409
 */

import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockRouterReplace = vi.fn();
const mockRouterPush = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: mockRouterReplace,
    push: mockRouterPush,
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// Mock motion/react to avoid animation complexity in tests
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
    h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h1 {...props}>{children}</h1>
    ),
    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p {...props}>{children}</p>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: {
          user: {
            email: 'alice@example.com',
            user_metadata: {},
          },
        },
      }),
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

const mockWorkspacesApiList = vi.fn();
const mockWorkspacesApiCreate = vi.fn();
const mockWorkspacesApiGet = vi.fn();

vi.mock('@/services/api/workspaces', () => ({
  workspacesApi: {
    list: (...args: unknown[]) => mockWorkspacesApiList(...args),
    create: (...args: unknown[]) => mockWorkspacesApiCreate(...args),
    get: (...args: unknown[]) => mockWorkspacesApiGet(...args),
  },
}));

const mockGetAuthProviderGetToken = vi.fn();

vi.mock('@/services/auth/providers', () => ({
  getAuthProvider: vi.fn(),
}));

const mockAddRecentWorkspace = vi.fn();

vi.mock('@/components/workspace-selector', () => ({
  WorkspaceSelector: () => <div data-testid="workspace-selector" />,
  addRecentWorkspace: (...args: unknown[]) => mockAddRecentWorkspace(...args),
}));

// Minimal UI component mocks
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button onClick={onClick} disabled={disabled}>
      {children}
    </button>
  ),
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock('@/components/ui/label', () => ({
  Label: ({ children }: { children: React.ReactNode }) => <label>{children}</label>,
}));

// ApiError mock — must be inside vi.mock factory (hoisted)
vi.mock('@/services/api/client', () => {
  class ApiError extends Error {
    status: number;
    type: string;
    isRetryable: boolean;
    constructor(problem: { title: string; status: number; type?: string }) {
      super(problem.title);
      this.status = problem.status;
      this.type = problem.type ?? 'about:blank';
      this.isRetryable = false;
      this.name = 'ApiError';
    }
  }
  return { ApiError };
});

// ---------------------------------------------------------------------------
// Import page component and ApiError (after mocks are set up)
// ---------------------------------------------------------------------------

import HomePage from '../page';
import { ApiError } from '@/services/api/client';
import { getAuthProvider } from '@/services/auth/providers';
import { supabase } from '@/lib/supabase';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('HomePage — auto-workspace creation (ONBD-01 / BUG-02)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Restore supabase user mock (vi.clearAllMocks clears call history only,
    // but implementations set inline in vi.mock factories need re-assertion
    // if afterEach called vi.restoreAllMocks())
    vi.mocked(supabase.auth.getUser).mockResolvedValue({
      data: {
        user: {
          id: 'user-123',
          email: 'alice@example.com',
          user_metadata: {},
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any,
      },
      error: null,
    });
    mockGetAuthProviderGetToken.mockResolvedValue('mock-token');
    vi.mocked(getAuthProvider).mockResolvedValue({
      getToken: () => mockGetAuthProviderGetToken(),
      login: vi.fn(),
      signup: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      restoreSession: vi.fn(),
    });
    // Default: no workspaces
    mockWorkspacesApiList.mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    // Do not call vi.restoreAllMocks() — it removes mock implementations set
    // via vi.mock() factories, which are re-established in beforeEach.
  });

  it('auto-creates workspace from email prefix when no workspaces exist', async () => {
    mockWorkspacesApiCreate.mockResolvedValue({
      id: 'uuid-1',
      name: 'alice',
      slug: 'alice-ab12',
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(mockWorkspacesApiCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'alice',
          slug: expect.stringMatching(/^alice-[a-z0-9]{4}$/),
        })
      );
    });

    await waitFor(() => {
      expect(mockRouterReplace).toHaveBeenCalledWith('/alice-ab12');
    });
  });

  it('retries with new suffix on 409 slug collision', async () => {
    const firstError = new ApiError({ title: 'Slug taken', status: 409 });
    mockWorkspacesApiCreate
      .mockRejectedValueOnce(firstError)
      .mockResolvedValueOnce({ id: 'uuid-2', name: 'alice', slug: 'alice-xy99' });

    render(<HomePage />);

    await waitFor(() => {
      expect(mockWorkspacesApiCreate).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(mockRouterReplace).toHaveBeenCalledWith('/alice-xy99');
    });
  });

  it('falls back to manual form when both create attempts fail with 409', async () => {
    const conflictError = new ApiError({ title: 'Slug taken', status: 409 });
    mockWorkspacesApiCreate.mockRejectedValue(conflictError);

    const { container } = render(<HomePage />);

    await waitFor(() => {
      expect(mockWorkspacesApiCreate).toHaveBeenCalledTimes(2);
    });

    // After both failures, should not navigate to a workspace
    expect(mockRouterReplace).not.toHaveBeenCalledWith(expect.stringMatching(/^\/[a-z]/));
    // Component renders something (fallback form)
    expect(container.firstChild).not.toBeNull();
  });
});
