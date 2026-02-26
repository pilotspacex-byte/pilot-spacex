/**
 * Unit tests for AttachmentPill component (TDD — component not yet created).
 *
 * Tests: filename display, remove button callback, uploading spinner state,
 * and error state display.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/AttachmentPill
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AttachmentContext } from '@/types/attachments';
import { AttachmentPill } from '../AttachmentPill';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeAttachment(overrides: Partial<AttachmentContext> = {}): AttachmentContext {
  return {
    id: 'local-1',
    filename: 'architecture.pdf',
    mime_type: 'application/pdf',
    size_bytes: 2048,
    source: 'local' as const,
    status: 'ready' as const,
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AttachmentPill', () => {
  const onRemove = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Filename display ─────────────────────────────────────────────────────

  it('shows_filename', () => {
    render(<AttachmentPill attachment={makeAttachment()} onRemove={onRemove} />);

    expect(screen.getByText('architecture.pdf')).toBeInTheDocument();
  });

  // ── Remove button ────────────────────────────────────────────────────────

  it('remove_button_calls_onRemove', async () => {
    const user = userEvent.setup();

    render(<AttachmentPill attachment={makeAttachment({ status: 'ready' })} onRemove={onRemove} />);

    const removeBtn = screen.getByRole('button', { name: /remove|delete|dismiss/i });
    await user.click(removeBtn);

    expect(onRemove).toHaveBeenCalledOnce();
  });

  // ── Uploading state ──────────────────────────────────────────────────────

  it('uploading_state_shows_spinner', () => {
    render(
      <AttachmentPill attachment={makeAttachment({ status: 'uploading' })} onRemove={onRemove} />
    );

    // Spinner must be present (role="status" or an SVG with animate-spin class)
    const spinner =
      screen.queryByRole('status') ?? document.querySelector('[class*="animate-spin"]');
    expect(spinner).not.toBeNull();
  });

  it('uploading_state_has_no_remove_button', () => {
    render(
      <AttachmentPill attachment={makeAttachment({ status: 'uploading' })} onRemove={onRemove} />
    );

    // No remove/delete button while upload is in flight
    expect(
      screen.queryByRole('button', { name: /remove|delete|dismiss/i })
    ).not.toBeInTheDocument();
  });

  // ── Error state ──────────────────────────────────────────────────────────

  it('error_state_shows_error_text', () => {
    render(
      <AttachmentPill
        attachment={makeAttachment({ status: 'error', error: 'Upload failed' })}
        onRemove={onRemove}
      />
    );

    expect(screen.getByText(/upload failed/i)).toBeInTheDocument();
  });
});
