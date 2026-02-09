'use client';

/**
 * HomepageUIStore - MobX store for Homepage Hub UI state (H043)
 * Manages chat expand/collapse and zone focus for keyboard navigation.
 * No server data — TanStack Query handles that per DD-065.
 */

import { makeAutoObservable, computed } from 'mobx';
import type { HomepageZone } from '../types';

export class HomepageUIStore {
  /** Whether the compact chat panel is expanded */
  chatExpanded = false;

  /** Currently focused zone for F6 keyboard cycling */
  activeZone: HomepageZone = 'activity';

  constructor() {
    makeAutoObservable(this, {
      isChatActive: computed,
    });
  }

  /** Whether the chat zone is currently active */
  get isChatActive(): boolean {
    return this.activeZone === 'chat';
  }

  expandChat(): void {
    this.chatExpanded = true;
    this.activeZone = 'chat';
  }

  collapseChat(): void {
    this.chatExpanded = false;
  }

  toggleChat(): void {
    if (this.chatExpanded) {
      this.collapseChat();
    } else {
      this.expandChat();
    }
  }

  setActiveZone(zone: HomepageZone): void {
    this.activeZone = zone;
  }

  reset(): void {
    this.chatExpanded = false;
    this.activeZone = 'activity';
  }
}
