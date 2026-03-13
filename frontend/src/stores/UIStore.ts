'use client';

import { makeAutoObservable, observable, reaction, computed, type IReactionDisposer } from 'mobx';
import { generateUUID } from '@/lib/utils';

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
  expandedNodes: string[];
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
  /** Expanded tree node IDs — MobX observable Set for sidebar tree state */
  expandedNodes: Set<string> = new Set<string>();

  private toastTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private reactionDisposers: IReactionDisposer[] = [];

  constructor() {
    makeAutoObservable(this, {
      activeToasts: computed,
      resolvedTheme: computed,
      hasOpenModal: computed,
      // CRITICAL: annotate as observable so MobX tracks Set mutations.
      // Standard Set mutations (add/delete) are NOT reactive without this.
      expandedNodes: observable,
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
        // Restore expanded nodes from persisted string array
        if (Array.isArray(state.expandedNodes)) {
          this.expandedNodes = new Set<string>(state.expandedNodes);
        }
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
        // Serialize Set as array for JSON storage
        expandedNodes: Array.from(this.expandedNodes),
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

  // ---------------------------------------------------------------------------
  // Tree expand state
  // ---------------------------------------------------------------------------

  toggleNodeExpanded(nodeId: string): void {
    if (this.expandedNodes.has(nodeId)) {
      this.expandedNodes.delete(nodeId);
    } else {
      this.expandedNodes.add(nodeId);
    }
  }

  isNodeExpanded(nodeId: string): boolean {
    return this.expandedNodes.has(nodeId);
  }

  // ---------------------------------------------------------------------------
  // Sidebar
  // ---------------------------------------------------------------------------

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
    const id = generateUUID();
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

/**
 * @deprecated Do NOT import this standalone instance in application code.
 * Use `useUIStore()` from `@/stores` to get the RootStore-scoped UIStore.
 * This singleton is a separate instance and does NOT share state with the
 * instance rendered by React components. Importing it for component logic
 * will cause subtle reactivity bugs (commands won't open dialogs, etc.).
 *
 * Kept only for use in non-React contexts (e.g. legacy scripts).
 */
export const uiStore = new UIStore();
