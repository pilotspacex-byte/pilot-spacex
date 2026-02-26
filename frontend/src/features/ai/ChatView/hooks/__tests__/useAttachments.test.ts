/**
 * Unit tests for useAttachments hook (TDD — component not yet created).
 *
 * Tests attachment lifecycle: add, remove, retry, reset, and
 * derived `attachmentIds` (ready-only).
 *
 * @module features/ai/ChatView/hooks/__tests__/useAttachments
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { AttachmentUploadResponse } from '@/types/attachments';

// ── Module mocks ────────────────────────────────────────────────────────────

vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: {
    upload: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { attachmentsApi } from '@/services/api/attachments';
import { toast } from 'sonner';
import { useAttachments } from '../useAttachments';

// ── Helpers ─────────────────────────────────────────────────────────────────

function makeFile(name: string, type: string, sizeBytes: number): File {
  const blob = new Blob(['x'.repeat(Math.min(sizeBytes, 10))], { type });
  const file = new File([blob], name, { type });
  // Override size (File.size is read-only in JSDOM, use Object.defineProperty)
  Object.defineProperty(file, 'size', { value: sizeBytes, configurable: true });
  return file;
}

function makeUploadResponse(filename: string): AttachmentUploadResponse {
  return {
    attachment_id: `srv-${filename}`,
    filename,
    mime_type: 'application/pdf',
    size_bytes: 1024,
    source: 'local' as const,
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('useAttachments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── addFile ──────────────────────────────────────────────────────────────

  it('addFile_valid_file_adds_to_list', async () => {
    const file = makeFile('report.pdf', 'application/pdf', 1024);
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('report.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.addFile(file);
    });

    // Immediately after add, attachment appears with uploading status
    expect(result.current.attachments).toHaveLength(1);
    expect(result.current.attachments[0]!.filename).toBe('report.pdf');
    expect(result.current.attachments[0]!.status).toBe('uploading');
  });

  it('addFile_oversized_file_shows_toast_error', async () => {
    // 26MB PDF — limit is 25MB
    const oversized = makeFile('huge.pdf', 'application/pdf', 26 * 1024 * 1024);

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.addFile(oversized);
    });

    expect(toast.error).toHaveBeenCalledOnce();
    expect(result.current.attachments).toHaveLength(0);
    expect(attachmentsApi.upload).not.toHaveBeenCalled();
  });

  it('addFile_unsupported_mime_type_shows_toast_error', async () => {
    const exe = makeFile('malware.exe', 'application/x-msdownload', 512);

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.addFile(exe);
    });

    expect(toast.error).toHaveBeenCalledOnce();
    expect(result.current.attachments).toHaveLength(0);
    expect(attachmentsApi.upload).not.toHaveBeenCalled();
  });

  it('addFile_max_5_files_blocks_6th', async () => {
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('file.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    // Add 5 valid files
    await act(async () => {
      for (let i = 1; i <= 5; i++) {
        result.current.addFile(makeFile(`doc${i}.pdf`, 'application/pdf', 1024));
      }
    });

    expect(result.current.attachments).toHaveLength(5);

    // 6th should be rejected
    act(() => {
      result.current.addFile(makeFile('doc6.pdf', 'application/pdf', 1024));
    });

    expect(toast.error).toHaveBeenCalledOnce();
    expect(result.current.attachments).toHaveLength(5);
  });

  // ── removeFile ───────────────────────────────────────────────────────────

  it('removeFile_removes_by_id', async () => {
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('a.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.addFile(makeFile('a.pdf', 'application/pdf', 1024));
      result.current.addFile(makeFile('b.pdf', 'application/pdf', 1024));
    });

    expect(result.current.attachments).toHaveLength(2);

    const firstId = result.current.attachments[0]!.id;

    act(() => {
      result.current.removeFile(firstId);
    });

    expect(result.current.attachments).toHaveLength(1);
    expect(result.current.attachments[0]!.filename).toBe('b.pdf');
  });

  // ── reset ────────────────────────────────────────────────────────────────

  it('reset_clears_all_attachments', async () => {
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('x.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.addFile(makeFile('x.pdf', 'application/pdf', 1024));
      result.current.addFile(makeFile('y.pdf', 'application/pdf', 1024));
      result.current.addFile(makeFile('z.pdf', 'application/pdf', 1024));
    });

    expect(result.current.attachments).toHaveLength(3);

    act(() => {
      result.current.reset();
    });

    expect(result.current.attachments).toHaveLength(0);
  });

  // ── addFromDrive ─────────────────────────────────────────────────────────

  it('addFromDrive_adds_ready_attachment', async () => {
    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    const response: AttachmentUploadResponse = {
      attachment_id: 'drive-123',
      filename: 'doc.gdoc',
      mime_type: 'application/vnd.google-apps.document',
      size_bytes: 2048,
      source: 'google_drive' as const,
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    };

    act(() => {
      result.current.addFromDrive(response);
    });

    expect(result.current.attachments).toHaveLength(1);
    expect(result.current.attachments[0]!.status).toBe('ready');
    expect(result.current.attachments[0]!.attachment_id).toBe('drive-123');
    expect(result.current.attachmentIds).toContain('drive-123');
  });

  it('addFromDrive_blocks_when_at_max_5', async () => {
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('f.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    // Fill to 5 via addFile
    await act(async () => {
      for (let i = 1; i <= 5; i++) {
        result.current.addFile(makeFile(`doc${i}.pdf`, 'application/pdf', 1024));
      }
    });

    const response: AttachmentUploadResponse = {
      attachment_id: 'drive-999',
      filename: 'extra.gdoc',
      mime_type: 'application/vnd.google-apps.document',
      size_bytes: 512,
      source: 'google_drive' as const,
      expires_at: new Date(Date.now() + 3600 * 1000).toISOString(),
    };

    act(() => {
      result.current.addFromDrive(response);
    });

    expect(toast.error).toHaveBeenCalledOnce();
    expect(result.current.attachments).toHaveLength(5);
  });

  // ── retry ────────────────────────────────────────────────────────────────

  it('retry_sets_error_status_for_id', async () => {
    vi.mocked(attachmentsApi.upload).mockResolvedValue(makeUploadResponse('r.pdf'));

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.addFile(makeFile('r.pdf', 'application/pdf', 1024));
    });

    const id = result.current.attachments[0]!.id;

    await act(async () => {
      await result.current.retry(id);
    });

    expect(result.current.attachments[0]!.status).toBe('error');
    expect(result.current.attachments[0]!.error).toMatch(/no longer available/i);
  });

  // ── attachmentIds ────────────────────────────────────────────────────────

  it('attachmentIds_only_includes_ready_attachments', async () => {
    // First upload resolves (ready), second stays pending (uploading)
    vi.mocked(attachmentsApi.upload)
      .mockResolvedValueOnce(makeUploadResponse('ready.pdf'))
      .mockImplementationOnce(
        () =>
          new Promise(() => {
            /* never resolves */
          })
      );

    const { result } = renderHook(() => useAttachments({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.addFile(makeFile('ready.pdf', 'application/pdf', 1024));
    });

    // Wait for upload to complete and status to update to 'ready'
    await waitFor(() => {
      const readyFiles = result.current.attachments.filter((a) => a.status === 'ready');
      expect(readyFiles).toHaveLength(1);
    });

    act(() => {
      result.current.addFile(makeFile('pending.pdf', 'application/pdf', 1024));
    });

    // Only the ready file's server id should appear in attachmentIds
    expect(result.current.attachmentIds).toHaveLength(1);
    expect(result.current.attachmentIds[0]).toBe('srv-ready.pdf');
  });
});
