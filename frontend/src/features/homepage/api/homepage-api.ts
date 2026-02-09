/**
 * Homepage Hub API Client - US-19
 * Follows the notesApi pattern from services/api/notes.ts.
 */

import { apiClient } from '@/services/api/client';
import type {
  HomepageActivityResponse,
  DigestResponse,
  DigestRefreshResponse,
  DismissSuggestionPayload,
  CreateNoteFromChatPayload,
  CreateNoteFromChatResponse,
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

  /** Fetch the latest AI digest suggestions for the current user. */
  getDigest(workspaceId: string): Promise<DigestResponse> {
    return apiClient.get<DigestResponse>(`/workspaces/${workspaceId}/homepage/digest`);
  },

  /** Trigger on-demand digest regeneration. */
  refreshDigest(workspaceId: string): Promise<DigestRefreshResponse> {
    return apiClient.post<DigestRefreshResponse>(
      `/workspaces/${workspaceId}/homepage/digest/refresh`
    );
  },

  /** Dismiss a digest suggestion (user-scoped, won't reappear for that entity). */
  dismissSuggestion(workspaceId: string, payload: DismissSuggestionPayload): Promise<void> {
    return apiClient.post<void>(`/workspaces/${workspaceId}/homepage/digest/dismiss`, payload);
  },

  /** Create a note from a homepage chat conversation. */
  createNoteFromChat(
    workspaceId: string,
    payload: CreateNoteFromChatPayload
  ): Promise<CreateNoteFromChatResponse> {
    return apiClient.post<CreateNoteFromChatResponse>(
      `/workspaces/${workspaceId}/notes/from-chat`,
      payload
    );
  },
};
