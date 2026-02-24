/**
 * Homepage Hub API Client - US-19
 * Follows the notesApi pattern from services/api/notes.ts.
 */

import { apiClient } from '@/services/api/client';
import type {
  DigestDismissPayload,
  DigestRefreshResponse,
  DigestResponse,
  HomepageActivityResponse,
} from '../types';

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

  /**
   * Fetch latest AI digest with user-filtered suggestions.
   */
  getDigest(workspaceId: string): Promise<DigestResponse> {
    return apiClient.get<DigestResponse>(`/workspaces/${workspaceId}/homepage/digest`);
  },

  /**
   * Trigger on-demand digest regeneration. Returns immediately with status.
   */
  refreshDigest(workspaceId: string): Promise<DigestRefreshResponse> {
    return apiClient.post<DigestRefreshResponse>(
      `/workspaces/${workspaceId}/homepage/digest/refresh`
    );
  },

  /**
   * Dismiss a digest suggestion so it no longer appears for this user.
   * Returns void (204 No Content from backend).
   */
  dismissSuggestion(workspaceId: string, payload: DigestDismissPayload): Promise<void> {
    return apiClient.post(`/workspaces/${workspaceId}/homepage/dismiss`, payload);
  },
};
