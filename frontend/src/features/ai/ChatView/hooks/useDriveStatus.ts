/**
 * useDriveStatus — TanStack Query hook for Google Drive connection status.
 *
 * Fetches whether the given workspace has an active Drive OAuth token.
 * Query is disabled when workspaceId is absent to avoid spurious requests
 * during initial render before workspace context is available.
 *
 * @module features/ai/ChatView/hooks/useDriveStatus
 */

import { useQuery } from '@tanstack/react-query';
import { attachmentsApi } from '@/services/api/attachments';
import type { DriveStatusResponse } from '@/types/attachments';

export function useDriveStatus(workspaceId: string | undefined) {
  return useQuery<DriveStatusResponse>({
    queryKey: ['drive-status', workspaceId],
    queryFn: () => attachmentsApi.getDriveStatus(workspaceId!),
    enabled: !!workspaceId,
    staleTime: 5_000,
    retry: false,
  });
}
