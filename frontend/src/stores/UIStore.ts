'use client';

import { makeAutoObservable, reaction, computed, type IReactionDisposer } from 'mobx';

export type Theme = 'light' | 'dark' | 'system';

export interface ModalState {
  isOpen: boolean;
  data?: unknown;
}

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: 'default' | 'success' | 'warning' | 'error';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const UI_STORAGE_KEY = 'pilot-space:ui-state';

interface PersistedUIState {
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  marginPanelWidth: number;
  theme: Theme;
}

export class UIStore {
  sidebarCollapsed = false;
  sidebarWidth = 260;
  marginPanelWidth = 200;
  theme: Theme = 'system';
  commandPaletteOpen = false;
  searchModalOpen = false;
  hydrated = false;

  modals: Map<string, ModalState> = new Map();
  toasts: Toast[] = [];

  private toastTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private reactionDisposers: IReactionDisposer[] = [];

  constructor() {
    makeAutoObservable(this, {
      activeToasts: computed,
      resolvedTheme: computed,
      hasOpenModal: computed,
    });

    this.setupPersistence();
  }

  hydrate(): void {
    if (this.hydrated) return;
    this.loadFromStorage();
    this.hydrated = true;
  }

  get activeToasts(): Toast[] {
    return this.toasts.slice(0, 5);
  }

  get resolvedTheme(): 'light' | 'dark' {
    if (this.theme !== 'system') {
      return this.theme;
    }

    if (typeof window === 'undefined') {
      return 'light';
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  get hasOpenModal(): boolean {
    for (const modal of this.modals.values()) {
      if (modal.isOpen) return true;
    }
    return false;
  }

  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(UI_STORAGE_KEY);
      if (stored) {
        const state: PersistedUIState = JSON.parse(stored);
        this.sidebarCollapsed = state.sidebarCollapsed ?? false;
        this.sidebarWidth = state.sidebarWidth ?? 260;
        this.marginPanelWidth = state.marginPanelWidth ?? 200;
        this.theme = state.theme ?? 'system';
      }
    } catch {
      // Ignore parse errors
    }
  }

  private setupPersistence(): void {
    const persistDisposer = reaction(
      () => ({
        sidebarCollapsed: this.sidebarCollapsed,
        sidebarWidth: this.sidebarWidth,
        marginPanelWidth: this.marginPanelWidth,
        theme: this.theme,
      }),
      (state) => {
        if (typeof window === 'undefined') return;

        try {
          localStorage.setItem(UI_STORAGE_KEY, JSON.stringify(state));
        } catch {
          // Ignore storage errors
        }
      }
    );

    const themeDisposer = reaction(
      () => this.resolvedTheme,
      (theme) => {
        if (typeof document === 'undefined') return;

        document.documentElement.classList.remove('light', 'dark');
        document.documentElement.classList.add(theme);
      },
      { fireImmediately: true }
    );

    this.reactionDisposers.push(persistDisposer, themeDisposer);
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  setSidebarCollapsed(collapsed: boolean): void {
    this.sidebarCollapsed = collapsed;
  }

  setSidebarWidth(width: number): void {
    this.sidebarWidth = Math.max(220, Math.min(400, width));
  }

  setMarginPanelWidth(width: number): void {
    this.marginPanelWidth = Math.max(150, Math.min(350, width));
  }

  setTheme(theme: Theme): void {
    this.theme = theme;
  }

  openCommandPalette(): void {
    this.commandPaletteOpen = true;
  }

  closeCommandPalette(): void {
    this.commandPaletteOpen = false;
  }

  toggleCommandPalette(): void {
    this.commandPaletteOpen = !this.commandPaletteOpen;
  }

  openSearchModal(): void {
    this.searchModalOpen = true;
  }

  closeSearchModal(): void {
    this.searchModalOpen = false;
  }

  toggleSearchModal(): void {
    this.searchModalOpen = !this.searchModalOpen;
  }

  openModal(id: string, data?: unknown): void {
    this.modals.set(id, { isOpen: true, data });
  }

  closeModal(id: string): void {
    const modal = this.modals.get(id);
    if (modal) {
      this.modals.set(id, { ...modal, isOpen: false });
    }
  }

  getModalState(id: string): ModalState | undefined {
    return this.modals.get(id);
  }

  isModalOpen(id: string): boolean {
    return this.modals.get(id)?.isOpen ?? false;
  }

  closeAllModals(): void {
    for (const [id, modal] of this.modals) {
      this.modals.set(id, { ...modal, isOpen: false });
    }
    this.commandPaletteOpen = false;
    this.searchModalOpen = false;
  }

  showToast(toast: Omit<Toast, 'id'>): string {
    const id = crypto.randomUUID();
    const duration = toast.duration ?? 5000;

    const newToast: Toast = {
      ...toast,
      id,
      duration,
    };

    this.toasts.unshift(newToast);

    if (duration > 0) {
      const timeout = setTimeout(() => {
        this.dismissToast(id);
      }, duration);
      this.toastTimeouts.set(id, timeout);
    }

    return id;
  }

  dismissToast(id: string): void {
    const timeout = this.toastTimeouts.get(id);
    if (timeout) {
      clearTimeout(timeout);
      this.toastTimeouts.delete(id);
    }

    this.toasts = this.toasts.filter((t) => t.id !== id);
  }

  clearAllToasts(): void {
    for (const timeout of this.toastTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.toastTimeouts.clear();
    this.toasts = [];
  }

  success(title: string, description?: string): string {
    return this.showToast({ title, description, variant: 'success' });
  }

  error(title: string, description?: string): string {
    return this.showToast({ title, description, variant: 'error', duration: 8000 });
  }

  warning(title: string, description?: string): string {
    return this.showToast({ title, description, variant: 'warning' });
  }

  info(title: string, description?: string): string {
    return this.showToast({ title, description, variant: 'default' });
  }

  reset(): void {
    this.sidebarCollapsed = false;
    this.sidebarWidth = 260;
    this.marginPanelWidth = 200;
    this.theme = 'system';
    this.commandPaletteOpen = false;
    this.searchModalOpen = false;
    this.modals.clear();
    this.clearAllToasts();
  }

  dispose(): void {
    for (const disposer of this.reactionDisposers) {
      disposer();
    }
    this.reactionDisposers = [];
    this.clearAllToasts();
  }
}

export const uiStore = new UIStore();
