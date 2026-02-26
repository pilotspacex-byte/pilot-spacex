/**
 * DriveFilePicker component tests (T043 — TDD).
 *
 * Tests: loading skeleton, file list rendering, folder navigation,
 * search input, selection state, and import flow.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/DriveFilePicker
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { DriveFilePicker } from '../DriveFilePicker';
import type { DriveFileItem, AttachmentUploadResponse } from '@/types/attachments';

// ── Module mocks ────────────────────────────────────────────────────────────

vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: {
    getDriveFiles: vi.fn(),
    importDriveFile: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { attachmentsApi } from '@/services/api/attachments';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const mockFolder: DriveFileItem = {
  id: 'folder-1',
  name: 'My Folder',
  mime_type: 'application/vnd.google-apps.folder',
  size_bytes: null,
  modified_at: '2026-01-01T00:00:00Z',
  is_folder: true,
  icon_url: null,
};

const mockFile1: DriveFileItem = {
  id: 'file-1',
  name: 'Report.pdf',
  mime_type: 'application/pdf',
  size_bytes: 102400,
  modified_at: '2026-01-10T00:00:00Z',
  is_folder: false,
  icon_url: null,
};

const mockFile2: DriveFileItem = {
  id: 'file-2',
  name: 'Notes.txt',
  mime_type: 'text/plain',
  size_bytes: 2048,
  modified_at: '2026-01-12T00:00:00Z',
  is_folder: false,
  icon_url: null,
};

const mockImportResponse: AttachmentUploadResponse = {
  attachment_id: 'att-drive-1',
  filename: 'Report.pdf',
  mime_type: 'application/pdf',
  size_bytes: 102400,
  source: 'google_drive',
  expires_at: '2026-02-01T00:00:00Z',
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

function renderPicker(props?: Partial<React.ComponentProps<typeof DriveFilePicker>>) {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    workspaceId: 'ws-1',
    onImported: vi.fn(),
  };
  return render(
    React.createElement(
      createWrapper(),
      null,
      React.createElement(DriveFilePicker, { ...defaultProps, ...props })
    )
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DriveFilePicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders_loading_skeleton', () => {
    // getDriveFiles never resolves → stays loading
    vi.mocked(attachmentsApi.getDriveFiles).mockReturnValue(new Promise(() => {}));

    renderPicker();

    // Skeleton placeholders should be visible
    const skeletons = document.querySelectorAll('[data-testid="drive-file-skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders_file_list', async () => {
    vi.mocked(attachmentsApi.getDriveFiles).mockResolvedValue({
      files: [mockFolder, mockFile1, mockFile2],
      next_page_token: null,
    });

    renderPicker();

    await waitFor(() => {
      expect(screen.getByText('My Folder')).toBeInTheDocument();
      expect(screen.getByText('Report.pdf')).toBeInTheDocument();
      expect(screen.getByText('Notes.txt')).toBeInTheDocument();
    });
  });

  it('folder_click_navigates', async () => {
    vi.mocked(attachmentsApi.getDriveFiles)
      .mockResolvedValueOnce({ files: [mockFolder], next_page_token: null })
      .mockResolvedValue({ files: [mockFile1], next_page_token: null });

    renderPicker();

    await waitFor(() => screen.getByText('My Folder'));

    fireEvent.click(screen.getByText('My Folder'));

    await waitFor(() => {
      // After navigating into folder, the folder's contents appear
      expect(screen.getByText('Report.pdf')).toBeInTheDocument();
    });

    // getDriveFiles should have been called with the folder id as parent_id
    expect(attachmentsApi.getDriveFiles).toHaveBeenCalledWith(
      'ws-1',
      expect.objectContaining({
        parent_id: 'folder-1',
      })
    );
  });

  it('renders_search_input', async () => {
    vi.mocked(attachmentsApi.getDriveFiles).mockResolvedValue({
      files: [],
      next_page_token: null,
    });

    renderPicker();

    const searchInput = screen.getByRole('textbox', { name: /search/i });
    expect(searchInput).toBeInTheDocument();
  });

  it('add_to_chat_disabled_without_selection', async () => {
    vi.mocked(attachmentsApi.getDriveFiles).mockResolvedValue({
      files: [mockFile1],
      next_page_token: null,
    });

    renderPicker();

    await waitFor(() => screen.getByText('Report.pdf'));

    const addButton = screen.getByRole('button', { name: /add to chat/i });
    expect(addButton).toBeDisabled();
  });

  it('file_click_enables_add_to_chat', async () => {
    vi.mocked(attachmentsApi.getDriveFiles).mockResolvedValue({
      files: [mockFile1],
      next_page_token: null,
    });

    renderPicker();

    await waitFor(() => screen.getByText('Report.pdf'));

    fireEvent.click(screen.getByText('Report.pdf'));

    const addButton = screen.getByRole('button', { name: /add to chat/i });
    expect(addButton).not.toBeDisabled();
  });

  it('add_to_chat_calls_import_and_closes', async () => {
    vi.mocked(attachmentsApi.getDriveFiles).mockResolvedValue({
      files: [mockFile1],
      next_page_token: null,
    });
    vi.mocked(attachmentsApi.importDriveFile).mockResolvedValue(mockImportResponse);

    const onImported = vi.fn();
    const onClose = vi.fn();

    renderPicker({ onImported, onClose });

    await waitFor(() => screen.getByText('Report.pdf'));

    fireEvent.click(screen.getByText('Report.pdf'));
    fireEvent.click(screen.getByRole('button', { name: /add to chat/i }));

    await waitFor(() => {
      expect(attachmentsApi.importDriveFile).toHaveBeenCalledWith(
        expect.objectContaining({
          workspace_id: 'ws-1',
          file_id: 'file-1',
          filename: 'Report.pdf',
          mime_type: 'application/pdf',
        })
      );
      expect(onImported).toHaveBeenCalledWith(mockImportResponse);
      expect(onClose).toHaveBeenCalled();
    });
  });
});
