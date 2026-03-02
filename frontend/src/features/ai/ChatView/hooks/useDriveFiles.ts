/**
 * useDriveFiles — TanStack Query hook for listing Google Drive files.
 *
 * Fetches files and folders from a workspace's connected Google Drive.
 * Supports folder navigation (parentId), full-text search, and pagination
 * via pageToken. Query is disabled when workspaceId is absent.
 *
 * @module features/ai/ChatView/hooks/useDriveFiles
 */

import { useQuery } from '@tanstack/react-query';
import { attachmentsApi } from '@/services/api/attachments';
import type { DriveFileListResponse } from '@/types/attachments';

interface UseDriveFilesParams {
  workspaceId: string;
  parentId?: string;
  search?: string;
  pageToken?: string;
}

export function useDriveFiles({ workspaceId, parentId, search, pageToken }: UseDriveFilesParams) {
  return useQuery<DriveFileListResponse>({
    queryKey: ['drive-files', workspaceId, parentId, search, pageToken],
    queryFn: () =>
      attachmentsApi.getDriveFiles(workspaceId, {
        parent_id: parentId,
        search: search || undefined,
        page_token: pageToken,
      }),
    enabled: !!workspaceId,
    staleTime: 30_000,
  });
}
