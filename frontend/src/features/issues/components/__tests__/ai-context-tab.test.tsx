/**
 * AIContextTab component tests (T009).
 *
 * Tests 4 states: empty, loading, error, results.
 * Tests Copy All, Regenerate, legacy fallback, partial failure.
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AIContextTab } from '../ai-context-tab';
import { useStore } from '@/stores';
import { generateFullContextMarkdown, copyToClipboard } from '@/lib/copy-context';

// Mock dependencies
vi.mock('mobx-react-lite', () => ({
  observer: (component: React.FC) => component,
}));

vi.mock('@/stores', () => ({
  useStore: vi.fn(),
}));

vi.mock('@/lib/copy-context', () => ({
  generateFullContextMarkdown: vi.fn(),
  generateSectionMarkdown: vi.fn(),
  copyToClipboard: vi.fn(),
}));

vi.mock('../ai-context-streaming', () => ({
  AIContextStreaming: ({ phases }: Record<string, unknown>) => (
    <div data-testid="ai-context-streaming">{(phases as Array<unknown>).length} phases</div>
  ),
}));

vi.mock('../context-summary-card', () => ({
  ContextSummaryCard: ({ summary }: Record<string, unknown>) => (
    <div data-testid="context-summary-card">{(summary as { title: string }).title}</div>
  ),
}));

vi.mock('../context-section', () => ({
  ContextSection: ({ title, children }: Record<string, unknown>) => (
    <div data-testid="context-section">
      <h3>{title as string}</h3>
      {children as React.ReactNode}
    </div>
  ),
}));

vi.mock('../related-issues-section', () => ({
  RelatedIssuesSection: () => <div data-testid="related-issues-section" />,
}));

vi.mock('../related-docs-section', () => ({
  RelatedDocsSection: () => <div data-testid="related-docs-section" />,
}));

vi.mock('../ai-tasks-section', () => ({
  AITasksSection: () => <div data-testid="ai-tasks-section" />,
}));

vi.mock('@/components/ui/button', () => ({
  Button: (props: Record<string, unknown>) => (
    <button
      onClick={props.onClick as React.MouseEventHandler}
      aria-label={props['aria-label'] as string}
    >
      {props.children as React.ReactNode}
    </button>
  ),
}));

vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: (props: Record<string, unknown>) => (
    <div className={props.className as string}>{props.children as React.ReactNode}</div>
  ),
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr data-testid="separator" />,
}));

describe('AIContextTab', () => {
  const mockContextStore: {
    isLoading: boolean;
    error: string | null;
    result: Record<string, unknown> | null;
    phases: Array<{ name: string; status: string }>;
    sectionErrors: Map<string, string>;
    hasStructuredData: boolean;
    generateContext: ReturnType<typeof vi.fn>;
    clearCache: ReturnType<typeof vi.fn>;
    abort: ReturnType<typeof vi.fn>;
  } = {
    isLoading: false,
    error: null,
    result: null,
    phases: [],
    sectionErrors: new Map(),
    hasStructuredData: false,
    generateContext: vi.fn(),
    clearCache: vi.fn(),
    abort: vi.fn(),
  };

  const createMockResult = (overrides?: Record<string, unknown>) => ({
    summary: null,
    relatedIssues: [],
    relatedDocs: [],
    tasks: [],
    prompts: [],
    phases: [],
    claudeCodePrompt: '',
    relatedDocs_legacy: [],
    relatedCode: [],
    similarIssues: [],
    ...overrides,
  });

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useStore).mockReturnValue({
      aiStore: { aiContext: mockContextStore },
    } as unknown as ReturnType<typeof useStore>);
    mockContextStore.isLoading = false;
    mockContextStore.error = null;
    mockContextStore.result = null;
    mockContextStore.phases = [];
    mockContextStore.sectionErrors = new Map();
    mockContextStore.hasStructuredData = false;
  });

  it('renders empty state with Generate button', () => {
    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByText('No AI Context Yet')).toBeInTheDocument();
    expect(
      screen.getByText(/Generate AI-powered context to get related issues/)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Generate AI context/i })).toBeInTheDocument();
  });

  it('calls generateContext on Generate button click', () => {
    render(<AIContextTab issueId="issue-1" />);

    const button = screen.getByRole('button', { name: /Generate AI context/i });
    fireEvent.click(button);

    expect(mockContextStore.generateContext).toHaveBeenCalledWith('issue-1');
  });

  it('renders loading state with AIContextStreaming', () => {
    mockContextStore.isLoading = true;
    mockContextStore.phases = [
      { name: 'Analyzing issue', status: 'in_progress' },
      { name: 'Finding related docs', status: 'pending' },
    ];

    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByTestId('ai-context-streaming')).toBeInTheDocument();
    expect(screen.getByText('2 phases')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    mockContextStore.error = 'API request failed';

    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByText('Failed to Generate Context')).toBeInTheDocument();
    expect(screen.getByText('API request failed')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Try generating context again/i })
    ).toBeInTheDocument();
  });

  it('calls generateContext on Try Again button click', () => {
    mockContextStore.error = 'API request failed';

    render(<AIContextTab issueId="issue-1" />);

    const button = screen.getByRole('button', {
      name: /Try generating context again/i,
    });
    fireEvent.click(button);

    expect(mockContextStore.generateContext).toHaveBeenCalledWith('issue-1');
  });

  it('renders results state with all sections', () => {
    mockContextStore.result = createMockResult({
      summary: {
        issueIdentifier: 'PS-123',
        title: 'Test Issue',
        summaryText: 'Test summary',
        stats: { relatedCount: 2, docsCount: 1, filesCount: 3, tasksCount: 2 },
      },
      relatedIssues: [{ identifier: 'PS-100' }],
      relatedDocs: [{ docType: 'note', title: 'Doc 1' }],
      tasks: [{ id: 1, title: 'Task 1' }],
      prompts: [{ taskId: 1, title: 'Prompt 1' }],
    });
    mockContextStore.hasStructuredData = true;

    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByText('Full Context for AI Implementation')).toBeInTheDocument();
    expect(screen.getByTestId('context-summary-card')).toBeInTheDocument();
    expect(screen.getByText('Related Context')).toBeInTheDocument();
    expect(screen.getByText('AI Tasks')).toBeInTheDocument();
  });

  it('calls Copy All handler and shows copied state', async () => {
    mockContextStore.result = createMockResult({
      summary: {
        issueIdentifier: 'PS-123',
        title: 'Test',
        summaryText: 'Summary',
        stats: { relatedCount: 0, docsCount: 0, filesCount: 0, tasksCount: 0 },
      },
    });
    mockContextStore.hasStructuredData = true;
    vi.mocked(copyToClipboard).mockResolvedValue(true);

    render(<AIContextTab issueId="issue-1" />);

    const button = screen.getByRole('button', { name: /Copy all context to clipboard/i });
    await act(async () => {
      fireEvent.click(button);
    });

    expect(generateFullContextMarkdown).toHaveBeenCalledWith(mockContextStore.result);
    expect(copyToClipboard).toHaveBeenCalled();
  });

  it('calls Regenerate handler after clearing cache', () => {
    mockContextStore.result = createMockResult({
      summary: {
        issueIdentifier: 'PS-123',
        title: 'Test',
        summaryText: 'Summary',
        stats: { relatedCount: 0, docsCount: 0, filesCount: 0, tasksCount: 0 },
      },
    });
    mockContextStore.hasStructuredData = true;

    render(<AIContextTab issueId="issue-1" />);

    const button = screen.getByRole('button', { name: /Regenerate AI context/i });
    fireEvent.click(button);

    expect(mockContextStore.clearCache).toHaveBeenCalledWith('issue-1');
    expect(mockContextStore.generateContext).toHaveBeenCalledWith('issue-1');
  });

  it('renders legacy fallback state', () => {
    mockContextStore.result = createMockResult();
    mockContextStore.hasStructuredData = false;

    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByText(/Context generated \(legacy format\)/)).toBeInTheDocument();
    expect(screen.getByText(/Regenerate for enhanced view/)).toBeInTheDocument();
  });

  it('renders partial failure state with Regenerate button', () => {
    mockContextStore.result = createMockResult();
    mockContextStore.hasStructuredData = false;
    mockContextStore.sectionErrors = new Map([
      ['summary', 'Failed to generate summary'],
      ['tasks', 'Failed to generate tasks'],
    ]);

    render(<AIContextTab issueId="issue-1" />);

    expect(screen.getByText('Partial Context Generation')).toBeInTheDocument();
    expect(screen.getByText(/Some sections failed to generate/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Regenerate AI context/i })).toBeInTheDocument();
  });
});
