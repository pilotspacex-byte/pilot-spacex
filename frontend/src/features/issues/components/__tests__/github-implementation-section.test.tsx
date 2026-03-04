/**
 * GitHubImplementationSection component tests.
 *
 * Verifies GitHub activity rendering (PRs / commits / branches), the
 * implementation plan panel (branch, task checklist, CLI commands, affected
 * graph nodes), and the generate-plan button states.
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GitHubImplementationSection } from '../github-implementation-section';
import type { IntegrationLink } from '@/types';
import type { GraphNodeDTO } from '@/types/knowledge-graph';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../../hooks/use-implementation-plan', () => ({
  useImplementationPlan: vi.fn(),
}));

vi.mock('../create-branch-popover', () => ({
  CreateBranchPopover: ({
    integrationId,
    workspaceId,
    issueId,
  }: {
    integrationId: string;
    workspaceId: string;
    issueId: string;
  }) => (
    <button
      data-testid="create-branch-popover"
      data-integration={integrationId}
      data-workspace={workspaceId}
      data-issue={issueId}
    >
      Create branch
    </button>
  ),
}));

// Import after mocking so the mock is applied
import { useImplementationPlan } from '../../hooks/use-implementation-plan';

const mockUseImplementationPlan = vi.mocked(useImplementationPlan);

// ---------------------------------------------------------------------------
// Helpers
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

function createBranchLink(overrides?: Partial<IntegrationLink>): IntegrationLink {
  return {
    id: 'branch-1',
    issueId: 'issue-1',
    integrationType: 'github_issue',
    externalId: 'feat/issue-1-fix-auth',
    externalUrl: 'https://github.com/org/repo/tree/feat/issue-1-fix-auth',
    link_type: 'branch',
    ...overrides,
  };
}

function createGraphNode(overrides?: Partial<GraphNodeDTO>): GraphNodeDTO {
  return {
    id: 'node-1',
    nodeType: 'code_reference',
    label: 'auth_module',
    properties: {},
    createdAt: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

/** Returns a no-plan state (hook returns no data, not loading). */
function noPlanState() {
  return { data: undefined, isLoading: false };
}

/** Returns a loading state for the plan hook. */
function loadingPlanState() {
  return { data: undefined, isLoading: true };
}

/** Returns a plan state with the given data shape. */
function withPlanData(overrides?: {
  suggestedBranch?: string;
  aiContext?: { tasksChecklist?: string[] };
}) {
  return {
    data: {
      suggestedBranch: 'feat/PS-42-auth-flow',
      aiContext: {
        tasksChecklist: ['Design auth schema', 'Implement JWT middleware', 'Add RLS policies'],
      },
      ...overrides,
    },
    isLoading: false,
  };
}

/** Opens the section by clicking the collapsible trigger (needed when defaultOpen=false). */
function openSection() {
  fireEvent.click(screen.getByRole('button', { name: /github & implementation/i }));
}

// ---------------------------------------------------------------------------
// Default render helper
// ---------------------------------------------------------------------------

interface RenderProps {
  pullRequests?: IntegrationLink[];
  commits?: IntegrationLink[];
  branches?: IntegrationLink[];
  isLoading?: boolean;
  integrationId?: string;
  workspaceId?: string;
  issueId?: string;
  issueIdentifier?: string;
  affectedNodes?: GraphNodeDTO[];
  onAffectedNodeClick?: (nodeId: string) => void;
  isGeneratingPlan?: boolean;
  onGeneratePlan?: () => void;
}

function renderComponent(props: RenderProps = {}) {
  return render(
    <GitHubImplementationSection
      pullRequests={props.pullRequests ?? []}
      commits={props.commits ?? []}
      branches={props.branches ?? []}
      isLoading={props.isLoading}
      integrationId={props.integrationId}
      workspaceId={props.workspaceId ?? 'ws-1'}
      issueId={props.issueId ?? 'issue-1'}
      issueIdentifier={props.issueIdentifier ?? 'PS-42'}
      affectedNodes={props.affectedNodes}
      onAffectedNodeClick={props.onAffectedNodeClick}
      isGeneratingPlan={props.isGeneratingPlan}
      onGeneratePlan={props.onGeneratePlan}
    />
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GitHubImplementationSection', () => {
  beforeEach(() => {
    mockUseImplementationPlan.mockReturnValue(
      noPlanState() as unknown as ReturnType<typeof useImplementationPlan>
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ---- section heading -------------------------------------------------------

  it('renders section title', () => {
    renderComponent();
    expect(screen.getByText('GitHub & Implementation')).toBeInTheDocument();
  });

  // ---- GitHub activity area --------------------------------------------------

  it('renders GitHub activity section with PRs', () => {
    const prs = [
      createPRLink({ id: 'pr-1', prNumber: 1, prTitle: 'First PR' }),
      createPRLink({ id: 'pr-2', prNumber: 2, prTitle: 'Second PR' }),
    ];
    renderComponent({ pullRequests: prs });

    expect(screen.getByText('First PR')).toBeInTheDocument();
    expect(screen.getByText('Second PR')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('renders commit list when commits provided', () => {
    const commits = [createCommitLink({ id: 'c-1', title: 'fix: resolve crash' })];
    renderComponent({ commits });

    expect(screen.getByText('fix: resolve crash')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  it('renders branch list when branches provided', () => {
    const branches = [createBranchLink({ id: 'b-1', externalId: 'feat/PS-42-auth-flow' })];
    renderComponent({ branches });

    expect(screen.getByText('feat/PS-42-auth-flow')).toBeInTheDocument();
  });

  it('renders total count badge as pullRequests + commits + branches', () => {
    const prs = [createPRLink({ id: 'pr-1' }), createPRLink({ id: 'pr-2' })];
    const commits = [createCommitLink({ id: 'c-1' }), createCommitLink({ id: 'c-2' })];
    const branches = [createBranchLink({ id: 'b-1' })];

    renderComponent({ pullRequests: prs, commits, branches });

    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders empty state when no GitHub activity', () => {
    renderComponent();
    openSection();

    expect(screen.getByText('No linked GitHub activity')).toBeInTheDocument();
  });

  it('shows loading skeletons when isLoading is true', () => {
    renderComponent({ pullRequests: [createPRLink()], isLoading: true });

    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('does not show implementation panel when loading', () => {
    mockUseImplementationPlan.mockReturnValue(
      loadingPlanState() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()] });

    expect(screen.queryByTestId('implementation-plan-panel')).not.toBeInTheDocument();
    expect(screen.getByText('Loading implementation plan…')).toBeInTheDocument();
  });

  // ---- implementation plan panel --------------------------------------------

  it('renders implementation plan when data available', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()] });

    expect(screen.getByTestId('implementation-plan-panel')).toBeInTheDocument();
    expect(screen.getByText('feat/PS-42-auth-flow')).toBeInTheDocument();
  });

  it('shows task checklist from implement context', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()] });

    expect(screen.getByTestId('task-checklist')).toBeInTheDocument();
    expect(screen.getByText('Design auth schema')).toBeInTheDocument();
    expect(screen.getByText('Implement JWT middleware')).toBeInTheDocument();
    expect(screen.getByText('Add RLS policies')).toBeInTheDocument();
  });

  it('does not render task checklist when no tasks in context', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData({ aiContext: { tasksChecklist: [] } }) as unknown as ReturnType<
        typeof useImplementationPlan
      >
    );

    renderComponent({ pullRequests: [createPRLink()] });

    expect(screen.queryByTestId('task-checklist')).not.toBeInTheDocument();
  });

  // ---- CLI commands ----------------------------------------------------------

  it('copies CLI command when copy button clicked', async () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderComponent({ pullRequests: [createPRLink()], issueIdentifier: 'PS-42' });

    await act(async () => {
      fireEvent.click(screen.getByTestId('copy-btn-interactive'));
    });

    expect(writeText).toHaveBeenCalledWith('pilot implement PS-42');
  });

  it('copies oneshot CLI command when oneshot copy button clicked', async () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderComponent({ pullRequests: [createPRLink()], issueIdentifier: 'PS-42' });

    await act(async () => {
      fireEvent.click(screen.getByTestId('copy-btn-oneshot-(ci)'));
    });

    expect(writeText).toHaveBeenCalledWith('pilot implement PS-42 --oneshot');
  });

  // ---- affected graph nodes -------------------------------------------------

  it('renders affected nodes when provided', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    const nodes: GraphNodeDTO[] = [
      createGraphNode({ id: 'n-1', label: 'auth_module', nodeType: 'code_reference' }),
      createGraphNode({ id: 'n-2', label: 'Chose Supabase', nodeType: 'decision' }),
    ];

    renderComponent({ pullRequests: [createPRLink()], affectedNodes: nodes });

    expect(screen.getByText('auth_module')).toBeInTheDocument();
    expect(screen.getByText('Chose Supabase')).toBeInTheDocument();
    // Abbreviations
    expect(screen.getByText('CR')).toBeInTheDocument();
    expect(screen.getByText('DE')).toBeInTheDocument();
  });

  it('calls onAffectedNodeClick when node chip clicked', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    const onAffectedNodeClick = vi.fn();
    const nodes: GraphNodeDTO[] = [
      createGraphNode({ id: 'node-abc', label: 'auth_module', nodeType: 'code_reference' }),
    ];

    renderComponent({
      pullRequests: [createPRLink()],
      affectedNodes: nodes,
      onAffectedNodeClick,
    });

    fireEvent.click(screen.getByTestId('node-chip-node-abc'));
    expect(onAffectedNodeClick).toHaveBeenCalledWith('node-abc');
  });

  it('does not render affected nodes section when affectedNodes is empty', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()], affectedNodes: [] });

    expect(screen.queryByText('Affected Graph Nodes')).not.toBeInTheDocument();
  });

  it('does not render affected nodes section when affectedNodes is not provided', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()] });

    expect(screen.queryByText(/affected graph nodes/i)).not.toBeInTheDocument();
  });

  // ---- generate plan button -------------------------------------------------

  it('shows generate plan button when no plan exists', () => {
    renderComponent();
    openSection();

    const btn = screen.getByTestId('generate-plan-btn');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent(/generate plan/i);
  });

  it('calls onGeneratePlan when generate plan button clicked', () => {
    const onGeneratePlan = vi.fn();
    renderComponent({ onGeneratePlan });
    openSection();

    fireEvent.click(screen.getByTestId('generate-plan-btn'));
    expect(onGeneratePlan).toHaveBeenCalledTimes(1);
  });

  it('disables generate plan button when isGeneratingPlan is true', () => {
    renderComponent({ isGeneratingPlan: true, onGeneratePlan: vi.fn() });
    openSection();

    const btn = screen.getByTestId('generate-plan-btn');
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/generating/i);
  });

  it('shows regenerate button inside plan panel when plan exists', () => {
    mockUseImplementationPlan.mockReturnValue(
      withPlanData() as unknown as ReturnType<typeof useImplementationPlan>
    );

    renderComponent({ pullRequests: [createPRLink()], onGeneratePlan: vi.fn() });

    const buttons = screen.getAllByTestId('generate-plan-btn');
    // At least one inside the implementation plan panel
    const regenBtn = buttons.find((b) => b.textContent?.includes('Regenerate'));
    expect(regenBtn).toBeDefined();
  });

  // ---- PR status badges ------------------------------------------------------

  it('renders PR status badge with correct capitalization', () => {
    renderComponent({ pullRequests: [createPRLink({ prStatus: 'merged' })] });
    expect(screen.getByText('Merged')).toBeInTheDocument();
  });

  it('renders closed PR status badge', () => {
    renderComponent({ pullRequests: [createPRLink({ prStatus: 'closed' })] });
    expect(screen.getByText('Closed')).toBeInTheDocument();
  });
});
