/**
 * ExtractionReviewPanel Tests — T-013/T-014
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import { ExtractionReviewPanel } from '../ExtractionReviewPanel';
import type { ExtractedIssue } from '../ExtractionReviewPanel';

// Mock AI API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    createExtractedIssues: vi.fn().mockResolvedValue({
      created_issues: ['id-1', 'id-2'],
      created_count: 2,
    }),
  },
}));

// Mock apiClient used by useAIRationale
vi.mock('@/services/api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

// Mock TanStack Query so useAIRationale doesn't fire real network requests in tests
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: vi.fn().mockReturnValue({ data: null, isLoading: false }),
  };
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const sampleIssues: ExtractedIssue[] = [
  {
    index: 0,
    title: 'Fix login page bug',
    description: 'Validation error on email field.',
    priority: 1,
    labels: ['bug'],
    confidenceScore: 0.95,
    confidenceTag: 'explicit',
    sourceBlockIds: ['block-1'],
    rationale: 'Explicitly mentioned as TODO',
  },
  {
    index: 1,
    title: 'Add rate limiting',
    description: 'Implement rate limiting for API.',
    priority: 2,
    labels: ['enhancement'],
    confidenceScore: 0.72,
    confidenceTag: 'implicit',
    sourceBlockIds: [],
    rationale: 'Implied from security context',
  },
];

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  issues: sampleIssues,
  isExtracting: false,
  error: null,
  workspaceId: 'ws-123',
  workspaceSlug: 'test-workspace',
  noteId: 'note-456',
  projectId: 'proj-789',
};

describe('ExtractionReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders panel header with issue count', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    expect(screen.getByText('(2 found)')).toBeDefined();
  });

  it('renders all issue cards', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    expect(screen.getByDisplayValue('Fix login page bug')).toBeDefined();
    expect(screen.getByDisplayValue('Add rate limiting')).toBeDefined();
  });

  it('shows confidence badges HIGH and MEDIUM', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    expect(screen.getByText('HIGH')).toBeDefined();
    expect(screen.getByText('MEDIUM')).toBeDefined();
  });

  it('shows priority badges', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    expect(screen.getByText('High')).toBeDefined();
    expect(screen.getByText('Medium')).toBeDefined();
  });

  it('all items are approved by default', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    const approvedButtons = screen.getAllByText('Approved');
    expect(approvedButtons).toHaveLength(2);
    // Footer shows "Create 2 Issues"
    expect(screen.getByText('Create 2 Issues')).toBeDefined();
  });

  it('toggles item to Skipped when Approved button is clicked', async () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    const approvedButtons = screen.getAllByText('Approved');
    fireEvent.click(approvedButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText('Skipped')).toBeDefined();
      expect(screen.getByText('Create 1 Issue')).toBeDefined();
    });
  });

  it('"Approve All" button approves all items', async () => {
    render(<ExtractionReviewPanel {...defaultProps} />);

    // Skip first item
    const approvedButtons = screen.getAllByText('Approved');
    fireEvent.click(approvedButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText('Approve All')).toBeDefined();
    });

    fireEvent.click(screen.getByText('Approve All'));

    await waitFor(() => {
      const approvedBtns = screen.getAllByText('Approved');
      expect(approvedBtns).toHaveLength(2);
    });
  });

  it('disables Create button when all items skipped', async () => {
    render(<ExtractionReviewPanel {...defaultProps} />);

    const approvedButtons = screen.getAllByText('Approved');
    fireEvent.click(approvedButtons[0]!);
    fireEvent.click(approvedButtons[1]!);

    await waitFor(() => {
      const createBtn = screen.getByText('Create 0 Issues').closest('button');
      expect(createBtn).toHaveProperty('disabled', true);
    });
  });

  it('expands rationale on toggle click', async () => {
    render(<ExtractionReviewPanel {...defaultProps} />);

    const rationaleButton = screen.getAllByText('Rationale')[0]!;
    fireEvent.click(rationaleButton);

    await waitFor(() => {
      expect(screen.getByText('Explicitly mentioned as TODO')).toBeDefined();
    });
  });

  it('shows loading skeleton when extracting with no issues', () => {
    render(<ExtractionReviewPanel {...defaultProps} issues={[]} isExtracting={true} />);
    // Skeleton renders divs — no review cards present
    expect(screen.queryByDisplayValue('Fix login page bug')).toBeNull();
  });

  it('shows empty state when extraction completes with no issues', () => {
    render(<ExtractionReviewPanel {...defaultProps} issues={[]} isExtracting={false} />);
    expect(screen.getByText('No actionable issues found in this note.')).toBeDefined();
  });

  it('shows extraction error', () => {
    render(
      <ExtractionReviewPanel
        {...defaultProps}
        issues={[]}
        error="Extraction failed. Please try again."
      />
    );
    expect(screen.getByText('Extraction failed. Please try again.')).toBeDefined();
  });

  it('calls aiApi.createExtractedIssues on Create button click', async () => {
    const { aiApi } = await import('@/services/api/ai');
    const onCreated = vi.fn();

    render(<ExtractionReviewPanel {...defaultProps} onCreated={onCreated} />);

    fireEvent.click(screen.getByText('Create 2 Issues'));

    await waitFor(() => {
      expect(aiApi.createExtractedIssues).toHaveBeenCalledWith(
        'ws-123',
        'note-456',
        expect.arrayContaining([
          expect.objectContaining({ title: 'Fix login page bug' }),
          expect.objectContaining({ title: 'Add rate limiting' }),
        ]),
        'proj-789'
      );
    });
  });

  it('allows editing issue title before creation', async () => {
    const { aiApi } = await import('@/services/api/ai');

    render(<ExtractionReviewPanel {...defaultProps} />);

    const titleInput = screen.getByDisplayValue('Fix login page bug');
    fireEvent.change(titleInput, { target: { value: 'Fix login page validation bug' } });

    fireEvent.click(screen.getByText('Create 2 Issues'));

    await waitFor(() => {
      expect(aiApi.createExtractedIssues).toHaveBeenCalledWith(
        'ws-123',
        'note-456',
        expect.arrayContaining([
          expect.objectContaining({ title: 'Fix login page validation bug' }),
        ]),
        'proj-789'
      );
    });
  });

  it('calls onOpenChange(false) on Cancel click', () => {
    const onOpenChange = vi.fn();
    render(<ExtractionReviewPanel {...defaultProps} onOpenChange={onOpenChange} />);

    fireEvent.click(screen.getByText('Cancel'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('renders AI rationale info buttons for each issue card (AIGOV-07)', () => {
    render(<ExtractionReviewPanel {...defaultProps} />);
    const infoButtons = screen.getAllByLabelText('View AI rationale');
    expect(infoButtons).toHaveLength(2);
  });
});
