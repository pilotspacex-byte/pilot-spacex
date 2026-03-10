/**
 * Notifications API client.
 *
 * T-031: Frontend API client for in-app notification management.
 *
 * Endpoints:
 * - GET  /workspaces/{id}/notifications              — paginated list
 * - GET  /workspaces/{id}/notifications/unread-count — bell badge count
 * - PATCH /workspaces/{id}/notifications/{id}/read   — mark single read
 * - POST /workspaces/{id}/notifications/read-all     — mark all read
 */

import { apiClient } from './client';

// ---------------------------------------------------------------------------
// Response types (matching backend NotificationResponse schema)
// ---------------------------------------------------------------------------

// Values match backend NotificationType enum (notification.py)
export type BackendNotificationPriority = 'low' | 'medium' | 'high' | 'urgent';
// Values match backend NotificationPriority enum (notification.py)
export type BackendNotificationType =
  | 'pr_review'
  | 'assignment'
  | 'sprint_deadline'
  | 'mention'
  | 'general';

export interface NotificationResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  type: BackendNotificationType;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  priority: BackendNotificationPriority;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UnreadCountResponse {
  count: number;
}

// ---------------------------------------------------------------------------
// Query params
// ---------------------------------------------------------------------------

export interface ListNotificationsParams {
  page?: number;
  page_size?: number;
  unread_only?: boolean;
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const notificationsApi = {
  /**
   * Fetch paginated notifications for a workspace.
   */
  list(
    workspaceId: string,
    params: ListNotificationsParams = {}
  ): Promise<NotificationListResponse> {
    const query: Record<string, string | number | boolean> = {};
    if (params.page !== undefined) query.page = params.page;
    if (params.page_size !== undefined) query.page_size = params.page_size;
    if (params.unread_only !== undefined) query.unread_only = params.unread_only;

    return apiClient.get<NotificationListResponse>(`/workspaces/${workspaceId}/notifications`, {
      params: query,
    });
  },

  /**
   * Get count of unread notifications for the bell badge.
   */
  getUnreadCount(workspaceId: string): Promise<UnreadCountResponse> {
    return apiClient.get<UnreadCountResponse>(
      `/workspaces/${workspaceId}/notifications/unread-count`
    );
  },

  /**
   * Mark a single notification as read.
   */
  markRead(workspaceId: string, notificationId: string): Promise<NotificationResponse> {
    return apiClient.patch<NotificationResponse>(
      `/workspaces/${workspaceId}/notifications/${notificationId}/read`
    );
  },

  /**
   * Mark all notifications as read for the current user.
   */
  markAllRead(workspaceId: string): Promise<void> {
    return apiClient.post<void>(`/workspaces/${workspaceId}/notifications/read-all`);
  },
};
