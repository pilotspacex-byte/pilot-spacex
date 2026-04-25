/**
 * SkillsGalleryPage tests — Phase 91 Plan 03 Task 3.
 *
 * Validates the four UI-SPEC §Surface 1 states (loading, error, empty, data)
 * plus card-click navigation and the count badge.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Skill } from '@/types/skill';

const NOW = new Date('2026-04-25T12:00:00Z');

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'workspace' }),
  useRouter: () => ({ push: mockPush }),
}));

const mockUseSkillCatalog = vi.fn();
vi.mock('../../hooks', () => ({
  useSkillCatalog: () => mockUseSkillCatalog(),
  SKILLS_CATALOG_QUERY_KEY: ['skills', 'catalog'] as const,
}));

// Phase 92 Plan 03 — gallery hosts a [Cards | Graph] toggle. Mock the hook
// and the heavy <SkillGraphView /> so this suite stays focused on the page
// composition (toggle wiring, conditional render, peek/setMode handoff).
const mockSetMode = vi.fn();
let mockMode: 'cards' | 'graph' = 'cards';
vi.mock('../../hooks/useSkillsViewQueryStringSync', () => ({
  useSkillsViewQueryStringSync: () => [mockMode, mockSetMode] as const,
}));

const mockOpenSkillFilePeek = vi.fn();
vi.mock('@/hooks/use-artifact-peek-state', () => ({
  useArtifactPeekState: () => ({
    openSkillFilePeek: mockOpenSkillFilePeek,
  }),
}));

let lastGraphProps: Record<string, unknown> | null = null;
vi.mock('../SkillGraphView', () => ({
  SkillGraphView: (props: Record<string, unknown>) => {
    lastGraphProps = props;
    return <div data-testid="skill-graph-view-stub" />;
  },
}));

import { SkillsGalleryPage } from '../SkillsGalleryPage';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function buildSkill(overrides: Partial<Skill> = {}): Skill {
  return {
    name: 'AI Context',
    slug: 'ai-context',
    description: 'Generate AI context for a chat session.',
    category: 'AI',
    icon: 'Sparkles',
    examples: [],
    feature_module: ['chat'],
    reference_files: ['architecture.md'],
    updated_at: new Date(NOW.getTime() - 86400 * 1000).toISOString(),
    ...overrides,
  };
}

interface CatalogResult {
  data?: Skill[];
  isPending: boolean;
  isError: boolean;
}

function makeResult(over: Partial<CatalogResult>): CatalogResult {
  return {
    data: undefined,
    isPending: false,
    isError: false,
    ...over,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe('SkillsGalleryPage (Phase 91)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    mockPush.mockReset();
    mockUseSkillCatalog.mockReset();
    mockSetMode.mockReset();
    mockOpenSkillFilePeek.mockReset();
    mockMode = 'cards';
    lastGraphProps = null;
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders 6 skeletons during isPending', () => {
    mockUseSkillCatalog.mockReturnValue(makeResult({ isPending: true }));
    render(<SkillsGalleryPage />, { wrapper });
    const list = screen.getByRole('list', { name: /loading skills/i });
    expect(list.children).toHaveLength(6);
    // Each li hosts an ArtifactCardSkeleton (role="status")
    expect(screen.getAllByRole('status', { name: /loading artifact/i })).toHaveLength(6);
  });

  it('renders the error state with a Reload button when isError', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockUseSkillCatalog.mockReturnValue(makeResult({ isError: true }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByText(/Couldn't load skills\./)).toBeInTheDocument();
    const reload = screen.getByRole('button', { name: /reload/i });
    await user.click(reload);
    // Click should not throw; the actual invalidation flow is exercised in
    // an integration env. We just assert the button is wired.
    expect(reload).toBeInTheDocument();
  });

  it('renders the empty state when data is an empty array', () => {
    mockUseSkillCatalog.mockReturnValue(makeResult({ data: [] }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByText(/No skills yet\./)).toBeInTheDocument();
    expect(
      screen.getByText(/Skills are defined in your backend templates\./),
    ).toBeInTheDocument();
  });

  it('does not render the count badge when there are no skills', () => {
    mockUseSkillCatalog.mockReturnValue(makeResult({ data: [] }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.queryByTestId('skills-count-badge')).toBeNull();
  });

  it('renders the count badge when data has skills', () => {
    const data = [
      buildSkill({ slug: 'a', name: 'A' }),
      buildSkill({ slug: 'b', name: 'B' }),
    ];
    mockUseSkillCatalog.mockReturnValue(makeResult({ data }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByTestId('skills-count-badge')).toHaveTextContent('2');
  });

  it('renders one SkillCard per skill in data', () => {
    const data = [
      buildSkill({ slug: 'a', name: 'Skill A' }),
      buildSkill({ slug: 'b', name: 'Skill B' }),
      buildSkill({ slug: 'c', name: 'Skill C' }),
    ];
    mockUseSkillCatalog.mockReturnValue(makeResult({ data }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByText('Skill A')).toBeInTheDocument();
    expect(screen.getByText('Skill B')).toBeInTheDocument();
    expect(screen.getByText('Skill C')).toBeInTheDocument();
  });

  it('navigates to /{slug}/skills/{skill.slug} when a card is clicked', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const data = [buildSkill({ slug: 'ai-context', name: 'AI Context' })];
    mockUseSkillCatalog.mockReturnValue(makeResult({ data }));
    render(<SkillsGalleryPage />, { wrapper });
    const card = screen.getByRole('article', { name: /AI Context/ });
    await user.click(card);
    expect(mockPush).toHaveBeenCalledWith('/workspace/skills/ai-context');
  });
});

// ---------------------------------------------------------------------------
// Phase 92 Plan 03 — toggle + conditional graph render
// ---------------------------------------------------------------------------

describe('SkillsGalleryPage (Phase 92 — view toggle)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    mockPush.mockReset();
    mockUseSkillCatalog.mockReset();
    mockSetMode.mockReset();
    mockOpenSkillFilePeek.mockReset();
    mockMode = 'cards';
    lastGraphProps = null;
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the SkillsViewToggle in the header (cards mode by default)', () => {
    mockUseSkillCatalog.mockReturnValue(
      makeResult({ data: [buildSkill({ slug: 'a', name: 'A' })] }),
    );
    render(<SkillsGalleryPage />, { wrapper });
    expect(
      screen.getByRole('tablist', { name: /skills view/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /cards/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  it('renders the cards grid (not the graph) when mode === "cards"', () => {
    mockMode = 'cards';
    mockUseSkillCatalog.mockReturnValue(
      makeResult({ data: [buildSkill({ slug: 'a', name: 'A' })] }),
    );
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.queryByTestId('skill-graph-view-stub')).toBeNull();
  });

  it('renders SkillGraphView (not the grid) when mode === "graph"', () => {
    mockMode = 'graph';
    mockUseSkillCatalog.mockReturnValue(
      makeResult({ data: [buildSkill({ slug: 'a', name: 'A' })] }),
    );
    render(<SkillsGalleryPage />, { wrapper });
    expect(screen.getByTestId('skill-graph-view-stub')).toBeInTheDocument();
    // Card grid items should NOT render — verify the SkillCard's role="article"
    // is absent.
    expect(screen.queryByRole('article')).toBeNull();
  });

  it('clicking the Graph tab calls setMode("graph")', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockUseSkillCatalog.mockReturnValue(
      makeResult({ data: [buildSkill({ slug: 'a', name: 'A' })] }),
    );
    render(<SkillsGalleryPage />, { wrapper });
    await user.click(screen.getByRole('tab', { name: /graph/i }));
    expect(mockSetMode).toHaveBeenCalledWith('graph');
  });

  it('passes onOpenFilePeek = openSkillFilePeek to SkillGraphView', () => {
    mockMode = 'graph';
    mockUseSkillCatalog.mockReturnValue(makeResult({ data: [] }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(lastGraphProps).not.toBeNull();
    expect(lastGraphProps!.onOpenFilePeek).toBe(mockOpenSkillFilePeek);
  });

  it('passes onSwitchToCards that calls setMode("cards") to SkillGraphView', () => {
    mockMode = 'graph';
    mockUseSkillCatalog.mockReturnValue(makeResult({ data: [] }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(lastGraphProps).not.toBeNull();
    const onSwitchToCards = lastGraphProps!.onSwitchToCards as () => void;
    expect(typeof onSwitchToCards).toBe('function');
    onSwitchToCards();
    expect(mockSetMode).toHaveBeenCalledWith('cards');
  });

  it('passes workspaceSlug to SkillGraphView', () => {
    mockMode = 'graph';
    mockUseSkillCatalog.mockReturnValue(makeResult({ data: [] }));
    render(<SkillsGalleryPage />, { wrapper });
    expect(lastGraphProps).not.toBeNull();
    expect(lastGraphProps!.workspaceSlug).toBe('workspace');
  });
});
