'use client';

import { makeAutoObservable, runInAction, computed } from 'mobx';
import { notificationsApi, type NotificationResponse } from '@/services/api/notifications';

// ---------------------------------------------------------------------------
// Public types (mapped from backend, kept compatible with existing consumers)
// ---------------------------------------------------------------------------

export type NotificationPriority = 'urgent' | 'important' | 'fyi';
export type NotificationType = 'issue' | 'pr' | 'mention' | 'comment' | 'system';

export interface Notification {
  id: string;
  title: string;
  /** Mapped from backend `body` field */
  description?: string;
  priority: NotificationPriority;
  type: NotificationType;
  /** true when read_at is non-null */
  read: boolean;
  /** Parsed from backend `created_at` ISO string */
  createdAt: Date;
  /** Nullable: entity link — not provided by backend directly */
  link?: string;
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

// Maps backend NotificationPriority enum values → UI priority labels.
// Backend values: 'low' | 'medium' | 'high' | 'urgent'
const PRIORITY_MAP: Record<string, NotificationPriority> = {
  low: 'fyi',
  medium: 'fyi',
  high: 'important',
  urgent: 'urgent',
};

// Maps backend NotificationType enum values → UI type groups.
// Backend values: 'pr_review' | 'assignment' | 'sprint_deadline' | 'mention' | 'general'
const TYPE_MAP: Record<string, NotificationType> = {
  pr_review: 'pr',
  assignment: 'issue',
  sprint_deadline: 'issue',
  mention: 'mention',
  general: 'system',
};

function mapNotification(raw: NotificationResponse): Notification {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.body || undefined,
    priority: PRIORITY_MAP[raw.priority] ?? 'fyi',
    type: TYPE_MAP[raw.type] ?? 'system',
    read: raw.read_at !== null,
    createdAt: new Date(raw.created_at),
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 30_000;

export class NotificationStore {
  notifications: Notification[] = [];
  totalPages = 0;
  currentPage = 1;
  /** Unread count from the dedicated backend endpoint (drives the bell badge) */
  unreadCount = 0;
  isLoading = false;
  error: string | null = null;

  private _pollingTimer: ReturnType<typeof setInterval> | null = null;
  private _pollingWorkspaceId: string | null = null;

  constructor() {
    makeAutoObservable(this, {
      sortedNotifications: computed,
      unreadNotifications: computed,
    });
  }

  // ---------------------------------------------------------------------------
  // Computed
  // ---------------------------------------------------------------------------

  get unreadNotifications(): Notification[] {
    return this.notifications.filter((n) => !n.read);
  }

  get sortedNotifications(): Notification[] {
    return [...this.notifications].sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  // ---------------------------------------------------------------------------
  // API actions
  // ---------------------------------------------------------------------------

  async fetchNotifications(workspaceId: string, page = 1): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const result = await notificationsApi.list(workspaceId, { page, page_size: 20 });
      runInAction(() => {
        if (page === 1) {
          this.notifications = result.items.map(mapNotification);
        } else {
          // Append for "load more" — avoid duplicates by id
          const existing = new Set(this.notifications.map((n) => n.id));
          const appended = result.items
            .filter((item) => !existing.has(item.id))
            .map(mapNotification);
          this.notifications = [...this.notifications, ...appended];
        }
        this.currentPage = result.page;
        this.totalPages = result.total_pages;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load notifications';
        this.isLoading = false;
      });
    }
  }

  async fetchUnreadCount(workspaceId: string): Promise<void> {
    try {
      const result = await notificationsApi.getUnreadCount(workspaceId);
      runInAction(() => {
        this.unreadCount = result.count;
      });
    } catch {
      // Non-fatal: polling failure should not surface an error to the user
    }
  }

  async markRead(workspaceId: string, notificationId: string): Promise<void> {
    try {
      const updated = await notificationsApi.markRead(workspaceId, notificationId);
      runInAction(() => {
        const idx = this.notifications.findIndex((n) => n.id === notificationId);
        if (idx !== -1) {
          this.notifications[idx] = mapNotification(updated);
        }
        if (this.unreadCount > 0) {
          this.unreadCount -= 1;
        }
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to mark notification as read';
      });
    }
  }

  async markAllRead(workspaceId: string): Promise<void> {
    try {
      await notificationsApi.markAllRead(workspaceId);
      runInAction(() => {
        this.notifications = this.notifications.map((n) => ({ ...n, read: true }));
        this.unreadCount = 0;
      });
    } catch (err) {
      runInAction(() => {
        this.error =
          err instanceof Error ? err.message : 'Failed to mark all notifications as read';
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Polling
  // ---------------------------------------------------------------------------

  startPolling(workspaceId: string): void {
    if (this._pollingWorkspaceId === workspaceId && this._pollingTimer !== null) {
      return;
    }
    this.stopPolling();
    this._pollingWorkspaceId = workspaceId;
    // Fetch immediately, then on interval
    void this.fetchUnreadCount(workspaceId);
    this._pollingTimer = setInterval(() => {
      void this.fetchUnreadCount(workspaceId);
    }, POLL_INTERVAL_MS);
  }

  stopPolling(): void {
    if (this._pollingTimer !== null) {
      clearInterval(this._pollingTimer);
      this._pollingTimer = null;
    }
    this._pollingWorkspaceId = null;
  }

  // ---------------------------------------------------------------------------
  // Legacy local-only actions (kept for backward compatibility)
  // These operate on the in-memory list only and do NOT call the API.
  // Callers that have a workspaceId should prefer the async API actions above.
  // ---------------------------------------------------------------------------

  /** @deprecated Use markRead(workspaceId, id) to persist to the backend. */
  markAsRead(id: string): void {
    const notification = this.notifications.find((n) => n.id === id);
    if (notification) {
      notification.read = true;
      if (this.unreadCount > 0) {
        this.unreadCount -= 1;
      }
    }
  }

  /** @deprecated Use markAllRead(workspaceId) to persist to the backend. */
  markAllAsRead(): void {
    this.notifications.forEach((n) => {
      n.read = true;
    });
    this.unreadCount = 0;
  }

  removeNotification(id: string): void {
    this.notifications = this.notifications.filter((n) => n.id !== id);
  }

  clearAll(): void {
    this.notifications = [];
  }

  reset(): void {
    this.stopPolling();
    this.notifications = [];
    this.totalPages = 0;
    this.currentPage = 1;
    this.unreadCount = 0;
    this.isLoading = false;
    this.error = null;
  }
}

export const notificationStore = new NotificationStore();
