/**
 * ExtractionPreviewModal Tests — Feature 009
 * Unit tests for the extraction preview modal component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { ExtractionPreviewModal } from '../ExtractionPreviewModal';
import type { ExtractedIssue } from '../ExtractionPreviewModal';

// Mock the AI API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    createExtractedIssues: vi.fn().mockResolvedValue({
      created_issue_ids: ['id-1', 'id-2'],
      count: 2,
    }),
  },
}));

// Mock supabase for SSE client auth
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

// Sample extracted issues
const sampleIssues: ExtractedIssue[] = [
  {
    index: 0,
    title: 'Fix login page bug',
    description: 'The login page has a validation error on the email field.',
    priority: 1,
    labels: ['bug', 'frontend'],
    confidenceScore: 0.95,
    confidenceTag: 'explicit',
    sourceBlockIds: ['block-1'],
    rationale: 'Explicitly mentioned as TODO',
  },
  {
    index: 1,
    title: 'Add rate limiting',
    description: 'Implement rate limiting for public API endpoints.',
    priority: 2,
    labels: ['enhancement'],
    confidenceScore: 0.72,
    confidenceTag: 'explicit',
    sourceBlockIds: ['block-2'],
    rationale: 'Mentioned as should-do',
  },
  {
    index: 2,
    title: 'Improve documentation',
    description: 'API docs need updating.',
    priority: 3,
    labels: ['docs'],
    confidenceScore: 0.45,
    confidenceTag: 'related',
    sourceBlockIds: [],
    rationale: 'Implied from context',
  },
];

describe('ExtractionPreviewModal', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    issues: sampleIssues,
    isExtracting: false,
    error: null,
    workspaceId: 'ws-123',
    noteId: 'note-456',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all extracted issues', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('Fix login page bug')).toBeDefined();
    expect(screen.getByText('Add rate limiting')).toBeDefined();
    expect(screen.getByText('Improve documentation')).toBeDefined();
  });

  it('shows priority badges', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('High')).toBeDefined();
    expect(screen.getByText('Medium')).toBeDefined();
    expect(screen.getByText('Low')).toBeDefined();
  });

  it('shows confidence scores', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('95% confidence')).toBeDefined();
    expect(screen.getByText('72% confidence')).toBeDefined();
    expect(screen.getByText('45% confidence')).toBeDefined();
  });

  it('shows labels as badges', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('bug')).toBeDefined();
    expect(screen.getByText('frontend')).toBeDefined();
    expect(screen.getByText('enhancement')).toBeDefined();
    expect(screen.getByText('docs')).toBeDefined();
  });

  it('has all issues selected by default', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    // The "Create 3 issues" button should reflect all selected
    expect(screen.getByText('Create 3 issues')).toBeDefined();
  });

  it('shows loading state when extracting', () => {
    render(<ExtractionPreviewModal {...defaultProps} issues={[]} isExtracting={true} />);

    expect(screen.getByText('Analyzing note content...')).toBeDefined();
  });

  it('shows error state', () => {
    render(<ExtractionPreviewModal {...defaultProps} issues={[]} error="API key not configured" />);

    expect(screen.getByText('API key not configured')).toBeDefined();
  });

  it('shows empty state when no issues found', () => {
    render(<ExtractionPreviewModal {...defaultProps} issues={[]} isExtracting={false} />);

    expect(screen.getByText('No actionable issues found in this note.')).toBeDefined();
  });

  it('calls onOpenChange(false) when Cancel is clicked', () => {
    const onOpenChange = vi.fn();
    render(<ExtractionPreviewModal {...defaultProps} onOpenChange={onOpenChange} />);

    fireEvent.click(screen.getByText('Cancel'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('deselects an issue when checkbox is toggled', async () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    // Initially 3 issues selected
    expect(screen.getByText('Create 3 issues')).toBeDefined();

    // Click on the first issue's checkbox (aria-label)
    const firstCheckbox = screen.getByLabelText('Select issue: Fix login page bug');
    fireEvent.click(firstCheckbox);

    // Now 2 issues selected
    await waitFor(() => {
      expect(screen.getByText('Create 2 issues')).toBeDefined();
    });
  });

  it('disables Create button when no issues selected', async () => {
    render(<ExtractionPreviewModal {...defaultProps} issues={[sampleIssues[0]!]} />);

    // Deselect the only issue
    const checkbox = screen.getByLabelText('Select issue: Fix login page bug');
    fireEvent.click(checkbox);

    await waitFor(() => {
      const createButton = screen.getByText('Create 0 issues');
      expect(createButton.closest('button')).toHaveProperty('disabled', true);
    });
  });

  it('shows select all / deselect all when multiple issues', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('Deselect all')).toBeDefined();
    expect(screen.getByText('3 of 3 selected')).toBeDefined();
  });

  it('shows extracting indicator with partial results', () => {
    render(
      <ExtractionPreviewModal {...defaultProps} issues={[sampleIssues[0]!]} isExtracting={true} />
    );

    expect(screen.getByText('Fix login page bug')).toBeDefined();
    expect(screen.getByText('Finding more issues...')).toBeDefined();
  });

  it('shows rationale text when available', () => {
    render(<ExtractionPreviewModal {...defaultProps} />);

    expect(screen.getByText('Explicitly mentioned as TODO')).toBeDefined();
    expect(screen.getByText('Mentioned as should-do')).toBeDefined();
  });

  it('creates issues on submit', async () => {
    const { aiApi } = await import('@/services/api/ai');
    const onCreated = vi.fn();

    render(<ExtractionPreviewModal {...defaultProps} onCreated={onCreated} />);

    const createButton = screen.getByText('Create 3 issues');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(aiApi.createExtractedIssues).toHaveBeenCalledWith(
        'ws-123',
        'note-456',
        expect.arrayContaining([expect.objectContaining({ title: 'Fix login page bug' })])
      );
    });
  });
});
