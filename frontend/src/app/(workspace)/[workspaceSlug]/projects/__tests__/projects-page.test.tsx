/**
 * Smoke test for ProjectsPage.
 *
 * Asserts NAV-04 sweep (Plan 90-05): the page-level search input has
 * been removed; the Command Palette v3 subsumes product search. Sibling
 * filters (sort, lead) and the create flow remain.
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

beforeAll(() => {
  // jsdom may stub localStorage incompletely; install a minimal in-memory shim.
  const store = new Map<string, string>();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, String(value)),
      removeItem: (key: string) => void store.delete(key),
      clear: () => void store.clear(),
      key: (i: number) => Array.from(store.keys())[i] ?? null,
      get length() {
        return store.size;
      },
    },
  });
});

const mockUseProjects = vi.fn();
vi.mock('@/features/projects/hooks', () => ({
  useProjects: (...args: unknown[]) => mockUseProjects(...args),
  selectAllProjects: (data: { items?: unknown[] } | undefined) => data?.items ?? [],
}));

vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: () => ({ currentWorkspaceId: 'ws-1', isAdmin: true }),
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'my-ws' }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/components/projects/ProjectCard', () => ({
  ProjectCard: ({ project }: { project: { id: string; name: string } }) => (
    <div data-testid={`project-card-${project.id}`}>{project.name}</div>
  ),
}));

vi.mock('@/components/projects/ProjectCardSkeleton', () => ({
  ProjectCardSkeleton: () => <div data-testid="project-card-skeleton" />,
}));

vi.mock('@/components/projects/CreateProjectModal', () => ({
  CreateProjectModal: () => null,
}));

async function renderPage() {
  mockUseProjects.mockReturnValue({
    data: { items: [{ id: 'p1', name: 'Alpha', identifier: 'ALPHA' }] },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });

  const { default: ProjectsPage } = await import('../page');
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>
    );
  });
  return result;
}

describe('ProjectsPage - NAV-04 sweep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render a page-level search input', async () => {
    await renderPage();
    expect(screen.queryByPlaceholderText(/search/i)).toBeNull();
  });
});
