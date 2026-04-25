/**
 * Smoke test for ArtifactsPage.
 *
 * Asserts NAV-04 sweep (Plan 90-05): the page-level filename search
 * input has been removed; Command Palette v3 subsumes product search.
 * Sort dropdown, table view, and download/delete actions remain.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'my-ws', projectId: 'proj-1' }),
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/stores', () => ({
  useStore: () => ({ workspaceStore: { currentWorkspace: { id: 'ws-1' } } }),
}));

const mockUseProjectArtifacts = vi.fn();
const mockUseDeleteArtifact = vi.fn();
const mockUseArtifactSignedUrl = vi.fn();
vi.mock('@/features/artifacts/hooks', () => ({
  useProjectArtifacts: (...args: unknown[]) => mockUseProjectArtifacts(...args),
  useDeleteArtifact: (...args: unknown[]) => mockUseDeleteArtifact(...args),
  useArtifactSignedUrl: (...args: unknown[]) => mockUseArtifactSignedUrl(...args),
}));

vi.mock('@/features/artifacts', () => ({
  FilePreviewModal: () => null,
}));

vi.mock('@/services/api/artifacts', () => ({
  artifactsApi: { getSignedUrl: vi.fn() },
}));

async function renderPage() {
  mockUseProjectArtifacts.mockReturnValue({
    data: [
      {
        id: 'a1',
        filename: 'spec.pdf',
        mimeType: 'application/pdf',
        sizeBytes: 1024,
        createdAt: '2025-01-01T00:00:00Z',
        uploader: null,
      },
    ],
    isLoading: false,
    isError: false,
  });
  mockUseArtifactSignedUrl.mockReturnValue({ data: undefined });
  mockUseDeleteArtifact.mockReturnValue({ mutate: vi.fn(), isPending: false });

  const { default: ArtifactsPage } = await import('../page');
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <QueryClientProvider client={queryClient}>
        <ArtifactsPage />
      </QueryClientProvider>
    );
  });
  return result;
}

describe('ArtifactsPage - NAV-04 sweep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render a page-level search input', async () => {
    await renderPage();
    expect(screen.queryByPlaceholderText(/search/i)).toBeNull();
  });
});
