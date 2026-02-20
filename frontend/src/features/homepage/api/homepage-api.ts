/**
 * Homepage Hub API Client - US-19
 * Follows the notesApi pattern from services/api/notes.ts.
 */

import { apiClient } from '@/services/api/client';
import type { HomepageActivityResponse } from '../types';

export const homepageApi = {
  /**
   * Fetch recent activity (notes + issues) grouped by day.
   * Supports cursor-based pagination for infinite scroll.
   */
  getActivity(workspaceId: string, cursor?: string): Promise<HomepageActivityResponse> {
    const params: Record<string, string> = {};
    if (cursor) params.cursor = cursor;

    return apiClient.get<HomepageActivityResponse>(`/workspaces/${workspaceId}/homepage/activity`, {
      params,
    });
  },
};
