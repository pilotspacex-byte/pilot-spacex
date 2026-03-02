/**
 * Unit tests for AttachmentChip component (TDD — component not yet created).
 *
 * Tests: filename display, absence of remove button (read-only history chip),
 * and file-type icon selection based on MIME type.
 *
 * @module features/ai/ChatView/MessageList/__tests__/AttachmentChip
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import type { AttachmentMetadata } from '@/types/attachments';
import { AttachmentChip } from '../AttachmentChip';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeMetadata(overrides: Partial<AttachmentMetadata> = {}): AttachmentMetadata {
  return {
    attachmentId: 'srv-abc-123',
    filename: 'design-spec.pdf',
    mimeType: 'application/pdf',
    source: 'local' as const,
    sizeBytes: 4096,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AttachmentChip', () => {
  // ── Filename display ─────────────────────────────────────────────────────

  it('renders_filename', () => {
    render(<AttachmentChip attachment={makeMetadata()} />);

    expect(screen.getByText('design-spec.pdf')).toBeInTheDocument();
  });

  // ── Read-only — no remove button ─────────────────────────────────────────

  it('no_remove_button', () => {
    render(<AttachmentChip attachment={makeMetadata()} />);

    // History chips are read-only — no interactive remove affordance
    expect(
      screen.queryByRole('button', { name: /remove|delete|dismiss/i })
    ).not.toBeInTheDocument();
  });

  // ── File icon by MIME type ────────────────────────────────────────────────

  it('shows_document_icon_for_pdf', () => {
    render(
      <AttachmentChip
        attachment={makeMetadata({ mimeType: 'application/pdf', filename: 'report.pdf' })}
      />
    );

    // Document/file icon: look for a test-id or aria-label tied to PDF/document icon
    const icon =
      screen.queryByTestId('icon-document') ??
      screen.queryByTestId('icon-file') ??
      document.querySelector('[data-file-type="document"]');

    expect(icon).not.toBeNull();
  });

  it('shows_image_icon_for_png', () => {
    render(
      <AttachmentChip
        attachment={makeMetadata({ mimeType: 'image/png', filename: 'screenshot.png' })}
      />
    );

    // Image icon: look for a test-id or aria-label tied to image icon
    const icon =
      screen.queryByTestId('icon-image') ?? document.querySelector('[data-file-type="image"]');

    expect(icon).not.toBeNull();
  });
});
