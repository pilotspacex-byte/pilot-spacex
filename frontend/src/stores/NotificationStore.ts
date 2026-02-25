'use client';

import { makeAutoObservable, computed } from 'mobx';
import { generateUUID } from '@/lib/utils';

export type NotificationPriority = 'urgent' | 'important' | 'fyi';
export type NotificationType = 'issue' | 'pr' | 'mention' | 'comment' | 'system';

export interface Notification {
  id: string;
  title: string;
  description?: string;
  priority: NotificationPriority;
  type: NotificationType;
  read: boolean;
  createdAt: Date;
  link?: string;
}

export class NotificationStore {
  notifications: Notification[] = [];

  constructor() {
    makeAutoObservable(this, {
      unreadCount: computed,
      unreadNotifications: computed,
      sortedNotifications: computed,
    });
  }

  get unreadCount(): number {
    return this.notifications.filter((n) => !n.read).length;
  }

  get unreadNotifications(): Notification[] {
    return this.notifications.filter((n) => !n.read);
  }

  get sortedNotifications(): Notification[] {
    return [...this.notifications].sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  addNotification(notification: Omit<Notification, 'id' | 'createdAt' | 'read'>): void {
    const newNotification: Notification = {
      ...notification,
      id: generateUUID(),
      createdAt: new Date(),
      read: false,
    };
    this.notifications.unshift(newNotification);
  }

  markAsRead(id: string): void {
    const notification = this.notifications.find((n) => n.id === id);
    if (notification) {
      notification.read = true;
    }
  }

  markAllAsRead(): void {
    this.notifications.forEach((n) => {
      n.read = true;
    });
  }

  removeNotification(id: string): void {
    this.notifications = this.notifications.filter((n) => n.id !== id);
  }

  clearAll(): void {
    this.notifications = [];
  }

  reset(): void {
    this.notifications = [];
  }
}

export const notificationStore = new NotificationStore();
