/**
 * ChunksTab tests — AUI-04, AUI-05
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';
import { ChunksTab } from '../ChunksTab';
import type { AttachmentExtractionResult, ExtractionChunk } from '@/types/attachments';

// Mock the ingest hook
vi.mock('../../hooks/useDocumentIngest', () => ({
  useDocumentIngest: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

const makeChunk = (i: number, heading = `Section ${i + 1}`): ExtractionChunk => ({
  chunkIndex: i,
  heading,
  content: `Content of section ${i + 1}`,
  charCount: 500 + i * 100,
  tokenCount: 125 + i * 25,
  headingHierarchy: [heading],
});

const CHUNKS = [makeChunk(0), makeChunk(1), makeChunk(2)];

const mockExtraction: AttachmentExtractionResult = {
  attachmentId: 'test-id',
  extractedText: 'Full text',
  metadata: {
    pageCount: 5,
    language: 'en',
    extractionSource: 'office',
    confidence: 0.95,
    wordCount: 300,
    providerName: null,
  },
  chunks: CHUNKS,
  tables: [],
};

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

function renderTab(overrides?: Partial<AttachmentExtractionResult>) {
  return render(
    <ChunksTab
      extraction={{ ...mockExtraction, ...overrides }}
      isLoading={false}
      artifactId="art-1"
      workspaceId="ws-1"
      projectId="proj-1"
    />,
    { wrapper: Wrapper }
  );
}

describe('ChunksTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(
      <ChunksTab extraction={undefined} isLoading={true} artifactId="art-1" workspaceId="ws-1" projectId="proj-1" />,
      { wrapper: Wrapper }
    );
    expect(screen.getByText(/Extraction in progress/)).toBeInTheDocument();
  });

  it('shows empty state when chunks is empty', () => {
    renderTab({ chunks: [] });
    expect(screen.getByTestId('chunks-empty')).toBeInTheDocument();
  });

  it('shows chunk count summary', () => {
    renderTab();
    expect(screen.getByTestId('chunk-summary')).toHaveTextContent('3 chunks included');
  });

  it('renders each chunk with heading label', () => {
    renderTab();
    expect(screen.getByTestId('chunk-heading-0')).toHaveTextContent('Chunk 1: Section 1');
    expect(screen.getByTestId('chunk-heading-1')).toHaveTextContent('Chunk 2: Section 2');
  });

  it('renders each chunk with char count', () => {
    renderTab();
    expect(screen.getByTestId('chunk-chars-0')).toHaveTextContent('500 chars');
  });

  it('renders each chunk with token estimate', () => {
    renderTab();
    expect(screen.getByTestId('chunk-tokens-0')).toHaveTextContent('~125 tokens');
  });

  it('toggling Switch marks chunk as excluded (grayed out)', async () => {
    renderTab();
    const card = screen.getByTestId('chunk-card-0');
    expect(card).not.toHaveClass('opacity-40');

    const toggle = screen.getAllByRole('switch')[0]!;
    fireEvent.click(toggle);

    expect(card).toHaveClass('opacity-40');
  });

  it('Reset button restores all chunks to included', () => {
    renderTab();
    // Exclude first chunk
    const toggle = screen.getAllByRole('switch')[0]!;
    fireEvent.click(toggle);
    expect(screen.getByTestId('chunk-card-0')).toHaveClass('opacity-40');

    // Reset
    fireEvent.click(screen.getByRole('button', { name: /reset/i }));
    expect(screen.getByTestId('chunk-card-0')).not.toHaveClass('opacity-40');
  });

  it('"Ingest to Knowledge Graph" button is disabled when chunks is empty', () => {
    renderTab({ chunks: [] });
    // Button doesn't render when chunks is empty (empty state shown instead)
    expect(screen.queryByTestId('ingest-button')).toBeNull();
  });

  it('"Ingest to Knowledge Graph" button calls mutate with excluded chunks', async () => {
    const { useDocumentIngest } = await import('../../hooks/useDocumentIngest');
    const mockMutate = vi.fn();
    vi.mocked(useDocumentIngest).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useDocumentIngest>);

    renderTab();
    // Exclude second chunk
    fireEvent.click(screen.getAllByRole('switch')[1]!);
    // Click ingest
    fireEvent.click(screen.getByTestId('ingest-button'));

    expect(mockMutate).toHaveBeenCalledWith([{ chunkIndex: 1, excluded: true }]);
  });
});
