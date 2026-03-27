/**
 * ExtractedTextTab tests - AUI-02
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ExtractedTextTab } from '../ExtractedTextTab';
import type { AttachmentExtractionResult } from '@/types/attachments';

const mockExtraction: AttachmentExtractionResult = {
  attachmentId: 'test-id',
  extractedText: '# Section 1\n\nSome content here.',
  metadata: {
    pageCount: 5,
    language: 'en',
    extractionSource: 'office',
    confidence: 0.95,
    wordCount: 100,
    providerName: null,
  },
  chunks: [],
  tables: [],
};

describe('ExtractedTextTab', () => {
  it('shows loading skeleton while isLoading is true', () => {
    render(<ExtractedTextTab extraction={undefined} isLoading={true} />);
    expect(screen.getByText(/Extraction in progress/)).toBeInTheDocument();
  });

  it('shows unavailable message when extractionSource is none', () => {
    const noExtraction: AttachmentExtractionResult = {
      ...mockExtraction,
      metadata: { ...mockExtraction.metadata, extractionSource: 'none' },
    };
    render(<ExtractedTextTab extraction={noExtraction} isLoading={false} />);
    expect(screen.getByText(/No extraction available/)).toBeInTheDocument();
  });

  it('renders extracted content area for office extraction', () => {
    render(<ExtractedTextTab extraction={mockExtraction} isLoading={false} />);
    expect(screen.getByTestId('extracted-text-markdown')).toBeInTheDocument();
  });

  it('renders monospace pre for OCR extraction', () => {
    const ocrExtraction: AttachmentExtractionResult = {
      ...mockExtraction,
      metadata: { ...mockExtraction.metadata, extractionSource: 'ocr' },
    };
    render(<ExtractedTextTab extraction={ocrExtraction} isLoading={false} />);
    expect(screen.getByTestId('extracted-text-ocr')).toBeInTheDocument();
  });

  it('shows provider footer when providerName is set', () => {
    const withProvider: AttachmentExtractionResult = {
      ...mockExtraction,
      metadata: { ...mockExtraction.metadata, providerName: 'HunyuanOCR' },
    };
    render(<ExtractedTextTab extraction={withProvider} isLoading={false} />);
    expect(screen.getByText(/Extraction powered by HunyuanOCR/)).toBeInTheDocument();
  });
});
