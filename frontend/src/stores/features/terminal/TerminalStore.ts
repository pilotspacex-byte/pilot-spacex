'use client';

import { makeAutoObservable } from 'mobx';

/**
 * MobX store managing terminal panel state.
 *
 * Tracks panel visibility, the active PTY session ID, and the panel height.
 * Does NOT manage xterm.js lifecycle — that is handled by the useTerminal hook.
 */
export class TerminalStore {
  /** Whether the terminal panel is currently visible. */
  isOpen: boolean = false;

  /** The session ID of the currently displayed PTY session, or null if none. */
  activeSessionId: string | null = null;

  /** Stored panel height in pixels (user-resizable). */
  panelHeight: number = 300;

  constructor() {
    makeAutoObservable(this);
  }

  /** Toggle the terminal panel open/closed. */
  toggle(): void {
    this.isOpen = !this.isOpen;
  }

  /** Open the terminal panel. */
  open(): void {
    this.isOpen = true;
  }

  /**
   * Hide the terminal panel.
   * Does NOT close the PTY session — the useTerminal hook handles cleanup.
   */
  close(): void {
    this.isOpen = false;
  }

  /** Set the active PTY session ID. */
  setActiveSession(id: string | null): void {
    this.activeSessionId = id;
  }

  /** Store the panel height (updated on user resize). */
  setPanelHeight(height: number): void {
    this.panelHeight = height;
  }

  /** Reset all fields to their initial defaults. */
  reset(): void {
    this.isOpen = false;
    this.activeSessionId = null;
    this.panelHeight = 300;
  }
}
