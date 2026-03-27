/**
 * MetadataPanel tests — AUI-01
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { MetadataPanel } from '../MetadataPanel';
import type { ExtractionMetadata } from '@/types/attachments';

const baseMetadata: ExtractionMetadata = {
  pageCount: 10,
  language: 'en',
  extractionSource: 'office',
  confidence: 0.95,
  wordCount: 2500,
  providerName: null,
};

function renderPanel(overrides?: Partial<ExtractionMetadata>) {
  return render(
    <MetadataPanel
      metadata={{ ...baseMetadata, ...overrides }}
      mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      sizeBytes={1024 * 1024 * 2}
      filename="report.docx"
    />
  );
}

describe('MetadataPanel', () => {
  it('renders page count', () => {
    renderPanel();
    expect(screen.getByTestId('metadata-page-count')).toHaveTextContent('10 pages');
  });

  it('renders singular page count', () => {
    renderPanel({ pageCount: 1 });
    expect(screen.getByTestId('metadata-page-count')).toHaveTextContent('1 page');
  });

  it('renders detected language', () => {
    renderPanel();
    expect(screen.getByTestId('metadata-language')).toHaveTextContent('English');
  });

  it('renders file size', () => {
    renderPanel();
    expect(screen.getByTestId('metadata-file-size')).toHaveTextContent('2.0 MB');
  });

  it('renders confidence badge green when confidence >= 0.9', () => {
    renderPanel({ confidence: 0.95 });
    expect(screen.getByText('95% confidence')).toHaveClass('bg-green-100');
  });

  it('renders confidence badge yellow when confidence 0.7-0.89', () => {
    renderPanel({ confidence: 0.8 });
    expect(screen.getByText('80% confidence')).toHaveClass('bg-yellow-100');
  });

  it('renders confidence badge red when confidence < 0.7', () => {
    renderPanel({ confidence: 0.6 });
    expect(screen.getByText('60% confidence')).toHaveClass('bg-red-100');
  });

  it('does not render confidence badge when confidence is null', () => {
    renderPanel({ confidence: null });
    expect(screen.queryByText(/confidence/)).toBeNull();
  });

  it('is collapsible - clicking trigger hides content', async () => {
    const user = userEvent.setup();
    renderPanel();
    expect(screen.getByTestId('metadata-page-count')).toBeVisible();
    await user.click(screen.getByRole('button', { name: /collapse/i }));
    // Radix CollapsibleContent removes the element from DOM when closed (no animation in JSDOM)
    expect(screen.queryByTestId('metadata-page-count')).toBeNull();
  });
});
