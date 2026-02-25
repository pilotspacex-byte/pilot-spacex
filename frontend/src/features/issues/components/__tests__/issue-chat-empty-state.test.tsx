/**
 * Unit tests for IssueChatEmptyState component.
 *
 * Tests:
 * - Renders heading text
 * - Shows/hides "Generate description" command based on issue.description
 * - Always shows Gather AI context, QA this issue, Decompose into tasks
 * - Calls onSendPrompt with the correct prompt when a command is clicked
 * - Renders NotePreviewCard for each noteLink
 * - Shows/hides "Related Notes" section based on noteLinks
 * - Shows hint text when no noteLinks and aiContextResult is null
 * - Hides hint when aiContextResult is not null
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { Issue } from '@/types';
import type { AIContextResult } from '@/stores/ai/AIContextStore';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T): T => component,
}));

vi.mock('../note-preview-card', () => ({
  NotePreviewCard: ({ noteTitle }: { noteTitle: string }) => (
    <div data-testid="note-preview">{noteTitle}</div>
  ),
}));

vi.mock('../issue-reference-card', () => ({
  IssueReferenceCard: ({ title }: { title: string }) => (
    <div data-testid="issue-reference">{title}</div>
  ),
}));

vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="icon-sparkles" />,
  Brain: () => <span data-testid="icon-brain" />,
  ShieldCheck: () => <span data-testid="icon-shield-check" />,
  ListTodo: () => <span data-testid="icon-list-todo" />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

import { IssueChatEmptyState } from '../issue-chat-empty-state';

const baseIssue: Issue = {
  id: 'issue-1',
  identifier: 'PS-42',
  name: 'Fix login bug',
  state: { id: 's1', name: 'todo', color: '#6B7280', group: 'unstarted' },
  priority: 'medium',
  projectId: 'p1',
  workspaceId: 'w1',
  sequenceId: 42,
  sortOrder: 1,
  reporterId: 'u1',
  reporter: { id: 'u1', email: 'u@e.com', displayName: 'User' },
  labels: [],
  subIssueCount: 0,
  project: { id: 'p1', name: 'P', identifier: 'PS' },
  hasAiEnhancements: false,
  createdAt: '2026-01-01',
  updatedAt: '2026-01-01',
};

const makeAIContextResult = (relatedIssues = []): AIContextResult => ({
  phases: [],
  claudeCodePrompt: '',
  relatedDocs_legacy: [],
  relatedCode: [],
  similarIssues: [],
  summary: null,
  relatedIssues,
  relatedDocs: [],
  tasks: [],
  prompts: [],
});

const DEFAULT_PROPS = {
  issue: baseIssue,
  aiContextResult: null,
  workspaceSlug: 'my-workspace',
  onSendPrompt: vi.fn(),
};

describe('IssueChatEmptyState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "How can I help with this issue?" heading', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} />);
    expect(screen.getByText('How can I help with this issue?')).toBeInTheDocument();
  });

  it('shows "Generate description" command when issue.description is falsy', () => {
    render(
      <IssueChatEmptyState {...DEFAULT_PROPS} issue={{ ...baseIssue, description: undefined }} />
    );
    expect(screen.getByText('Generate description')).toBeInTheDocument();
  });

  it('shows "Generate description" when description is empty string', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} issue={{ ...baseIssue, description: '' }} />);
    expect(screen.getByText('Generate description')).toBeInTheDocument();
  });

  it('hides "Generate description" command when issue.description is present', () => {
    render(
      <IssueChatEmptyState
        {...DEFAULT_PROPS}
        issue={{ ...baseIssue, description: 'Some existing description' }}
      />
    );
    expect(screen.queryByText('Generate description')).not.toBeInTheDocument();
  });

  it('always shows "Gather AI context"', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} />);
    expect(screen.getByText('Gather AI context')).toBeInTheDocument();
  });

  it('always shows "QA this issue"', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} />);
    expect(screen.getByText('QA this issue')).toBeInTheDocument();
  });

  it('always shows "Decompose into tasks"', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} />);
    expect(screen.getByText('Decompose into tasks')).toBeInTheDocument();
  });

  it('calls onSendPrompt with correct prompt when "Gather AI context" is clicked', () => {
    const onSendPrompt = vi.fn();
    render(<IssueChatEmptyState {...DEFAULT_PROPS} onSendPrompt={onSendPrompt} />);
    fireEvent.click(screen.getByText('Gather AI context'));
    expect(onSendPrompt).toHaveBeenCalledOnce();
    expect(onSendPrompt).toHaveBeenCalledWith(
      expect.stringContaining('Analyze this issue and gather full implementation context')
    );
  });

  it('calls onSendPrompt with correct prompt when "QA this issue" is clicked', () => {
    const onSendPrompt = vi.fn();
    render(<IssueChatEmptyState {...DEFAULT_PROPS} onSendPrompt={onSendPrompt} />);
    fireEvent.click(screen.getByText('QA this issue'));
    expect(onSendPrompt).toHaveBeenCalledOnce();
    expect(onSendPrompt).toHaveBeenCalledWith(
      expect.stringContaining('Review this issue for completeness')
    );
  });

  it('calls onSendPrompt with correct prompt when "Decompose into tasks" is clicked', () => {
    const onSendPrompt = vi.fn();
    render(<IssueChatEmptyState {...DEFAULT_PROPS} onSendPrompt={onSendPrompt} />);
    fireEvent.click(screen.getByText('Decompose into tasks'));
    expect(onSendPrompt).toHaveBeenCalledOnce();
    expect(onSendPrompt).toHaveBeenCalledWith(
      expect.stringContaining('Decompose this issue into atomic implementation tasks')
    );
  });

  it('calls onSendPrompt with correct prompt when "Generate description" is clicked', () => {
    const onSendPrompt = vi.fn();
    render(
      <IssueChatEmptyState
        {...DEFAULT_PROPS}
        issue={{ ...baseIssue, description: undefined }}
        onSendPrompt={onSendPrompt}
      />
    );
    fireEvent.click(screen.getByText('Generate description'));
    expect(onSendPrompt).toHaveBeenCalledOnce();
    expect(onSendPrompt).toHaveBeenCalledWith(
      expect.stringContaining('Generate a detailed description for issue')
    );
  });

  it('renders NotePreviewCard for each noteLink in issue.noteLinks', () => {
    const issueWithLinks = {
      ...baseIssue,
      noteLinks: [
        {
          id: 'link-1',
          noteId: 'n1',
          issueId: 'issue-1',
          linkType: 'CREATED' as const,
          noteTitle: 'Note One',
        },
        {
          id: 'link-2',
          noteId: 'n2',
          issueId: 'issue-1',
          linkType: 'EXTRACTED' as const,
          noteTitle: 'Note Two',
        },
      ],
    };

    render(<IssueChatEmptyState {...DEFAULT_PROPS} issue={issueWithLinks} />);

    const cards = screen.getAllByTestId('note-preview');
    expect(cards).toHaveLength(2);
    expect(screen.getByText('Note One')).toBeInTheDocument();
    expect(screen.getByText('Note Two')).toBeInTheDocument();
  });

  it('renders "Related Notes" section when noteLinks exist', () => {
    const issueWithLinks = {
      ...baseIssue,
      noteLinks: [
        {
          id: 'link-1',
          noteId: 'n1',
          issueId: 'issue-1',
          linkType: 'CREATED' as const,
          noteTitle: 'Note One',
        },
      ],
    };

    render(<IssueChatEmptyState {...DEFAULT_PROPS} issue={issueWithLinks} />);
    expect(screen.getByText('Related Notes')).toBeInTheDocument();
  });

  it('hides "Related Notes" section when noteLinks is empty', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} issue={{ ...baseIssue, noteLinks: [] }} />);
    expect(screen.queryByText('Related Notes')).not.toBeInTheDocument();
  });

  it('hides "Related Notes" section when noteLinks is absent', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} issue={baseIssue} />);
    expect(screen.queryByText('Related Notes')).not.toBeInTheDocument();
  });

  it('renders hint text when no noteLinks and aiContextResult is null', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} aiContextResult={null} />);
    // The hint paragraph contains unique text "discover related notes and issues"
    expect(screen.getByText(/discover related notes and issues/)).toBeInTheDocument();
  });

  it('hides hint when aiContextResult is not null', () => {
    render(<IssueChatEmptyState {...DEFAULT_PROPS} aiContextResult={makeAIContextResult()} />);
    // The hint text "Run 'Gather AI context' to discover..." should not appear
    // We check for the specific hint paragraph text fragment
    expect(screen.queryByText(/to discover related notes and issues/)).not.toBeInTheDocument();
  });

  it('hides hint when noteLinks exist (even if aiContextResult is null)', () => {
    const issueWithLinks = {
      ...baseIssue,
      noteLinks: [
        {
          id: 'link-1',
          noteId: 'n1',
          issueId: 'issue-1',
          linkType: 'CREATED' as const,
          noteTitle: 'Note',
        },
      ],
    };

    render(
      <IssueChatEmptyState {...DEFAULT_PROPS} issue={issueWithLinks} aiContextResult={null} />
    );

    expect(screen.queryByText(/to discover related notes and issues/)).not.toBeInTheDocument();
  });
});
