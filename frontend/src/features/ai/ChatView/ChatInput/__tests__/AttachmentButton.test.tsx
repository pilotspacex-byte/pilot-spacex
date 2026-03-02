/**
 * Unit tests for AttachmentButton component (TDD — component not yet created).
 *
 * Tests: paperclip button rendering, drag-over overlay visibility,
 * drag-leave overlay dismissal, and unsupported file-type error on drop.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/AttachmentButton
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AttachmentButton } from '../AttachmentButton';

// ── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

import { toast } from 'sonner';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeDataTransfer(files: File[]): DataTransfer {
  return {
    files: files as unknown as FileList,
    items: files.map((f) => ({
      kind: 'file',
      type: f.type,
      getAsFile: () => f,
    })) as unknown as DataTransferItemList,
    types: ['Files'],
    dropEffect: 'none',
    effectAllowed: 'all',
    clearData: vi.fn(),
    getData: vi.fn(),
    setData: vi.fn(),
    setDragImage: vi.fn(),
  } as unknown as DataTransfer;
}

function makeFile(name: string, type: string): File {
  return new File(['content'], name, { type });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AttachmentButton', () => {
  const onAddFile = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Rendering ────────────────────────────────────────────────────────────

  it('renders_paperclip_button', () => {
    render(<AttachmentButton onAddFile={onAddFile} />);

    // Should render a button with accessible label
    const button = screen.getByRole('button', { name: /attach|paperclip|file/i });
    expect(button).toBeInTheDocument();
  });

  // ── Drag-over overlay ────────────────────────────────────────────────────

  it('drag_over_shows_overlay', () => {
    const { container } = render(<AttachmentButton onAddFile={onAddFile} />);

    fireEvent.dragOver(container.firstElementChild!);

    expect(screen.getByText(/drop to attach/i)).toBeInTheDocument();
  });

  it('drag_leave_hides_overlay', () => {
    const { container } = render(<AttachmentButton onAddFile={onAddFile} />);

    const root = container.firstElementChild!;
    fireEvent.dragOver(root);

    expect(screen.getByText(/drop to attach/i)).toBeInTheDocument();

    fireEvent.dragLeave(root);

    expect(screen.queryByText(/drop to attach/i)).not.toBeInTheDocument();
  });

  // ── Drop validation ──────────────────────────────────────────────────────

  it('drop_unsupported_type_shows_error', () => {
    const { container } = render(<AttachmentButton onAddFile={onAddFile} />);
    const exe = makeFile('virus.exe', 'application/x-msdownload');

    fireEvent.drop(container.firstElementChild!, {
      dataTransfer: makeDataTransfer([exe]),
    });

    expect(toast.error).toHaveBeenCalledOnce();
    expect(onAddFile).not.toHaveBeenCalled();
  });

  it('drop_valid_file_calls_onAddFile', () => {
    const { container } = render(<AttachmentButton onAddFile={onAddFile} />);
    const pdf = makeFile('report.pdf', 'application/pdf');

    fireEvent.drop(container.firstElementChild!, {
      dataTransfer: makeDataTransfer([pdf]),
    });

    expect(onAddFile).toHaveBeenCalledOnce();
    expect(onAddFile).toHaveBeenCalledWith(pdf);
    expect(toast.error).not.toHaveBeenCalled();
  });

  // ── Drive button ──────────────────────────────────────────────────────────

  it('drive_button_not_rendered_without_handlers', () => {
    render(<AttachmentButton onAddFile={onAddFile} />);
    expect(screen.queryByTestId('drive-button')).not.toBeInTheDocument();
  });

  it('drive_button_calls_onConnectDrive_when_not_connected', () => {
    const onConnectDrive = vi.fn();
    render(
      <AttachmentButton
        onAddFile={onAddFile}
        driveConnected={false}
        onConnectDrive={onConnectDrive}
      />
    );

    fireEvent.click(screen.getByTestId('drive-button'));
    expect(onConnectDrive).toHaveBeenCalledOnce();
  });

  it('drive_button_calls_onOpenDrivePicker_when_connected', () => {
    const onOpenDrivePicker = vi.fn();
    render(
      <AttachmentButton
        onAddFile={onAddFile}
        driveConnected={true}
        onOpenDrivePicker={onOpenDrivePicker}
      />
    );

    fireEvent.click(screen.getByTestId('drive-button'));
    expect(onOpenDrivePicker).toHaveBeenCalledOnce();
  });
});
