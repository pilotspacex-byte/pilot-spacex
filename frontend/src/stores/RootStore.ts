'use client';

import { createContext, useContext } from 'react';
import { AuthStore } from './AuthStore';
import { UIStore } from './UIStore';
import { WorkspaceStore } from './WorkspaceStore';
import { NotificationStore } from './NotificationStore';
import { NoteStore } from './features/notes/NoteStore';
import { IssueStore } from './features/issues/IssueStore';
import { CycleStore } from './features/cycles/CycleStore';
import { AIStore, getAIStore } from './ai';
import { OnboardingStore } from './OnboardingStore';
import { RoleSkillStore } from './RoleSkillStore';
import { HomepageUIStore } from '@/features/homepage/stores/HomepageUIStore';

export class RootStore {
  auth: AuthStore;
  ui: UIStore;
  workspace: WorkspaceStore;
  notifications: NotificationStore;
  notes: NoteStore;
  issues: IssueStore;
  cycles: CycleStore;
  ai: AIStore;
  onboarding: OnboardingStore;
  roleSkill: RoleSkillStore;
  homepage: HomepageUIStore;

  constructor() {
    this.auth = new AuthStore();
    this.ui = new UIStore();
    this.workspace = new WorkspaceStore();
    this.notifications = new NotificationStore();
    this.notes = new NoteStore();
    this.issues = new IssueStore();
    this.cycles = new CycleStore();
    this.ai = getAIStore();
    this.onboarding = new OnboardingStore();
    this.roleSkill = new RoleSkillStore();
    this.homepage = new HomepageUIStore();

    // Wire cross-store references
    this.workspace.setAuthStore(this.auth);
  }

  reset(): void {
    this.workspace.reset();
    this.notifications.reset();
    this.notes.reset();
    this.issues.reset();
    this.cycles.reset();
    this.ui.reset();
    this.ai.reset();
    this.onboarding.reset();
    this.roleSkill.reset();
    this.homepage.reset();
  }

  dispose(): void {
    this.auth.dispose();
    this.ui.dispose();
    this.onboarding.dispose();
  }
}

export const rootStore = new RootStore();

export const StoreContext = createContext<RootStore | null>(null);

export function useStores(): RootStore {
  const store = useContext(StoreContext);
  if (!store) {
    throw new Error('useStores must be used within a StoreProvider');
  }
  return store;
}

export function useAuthStore(): AuthStore {
  return useStores().auth;
}

export function useUIStore(): UIStore {
  return useStores().ui;
}

export function useWorkspaceStore(): WorkspaceStore {
  return useStores().workspace;
}

export function useNotificationStore(): NotificationStore {
  return useStores().notifications;
}

export function useNoteStore(): NoteStore {
  return useStores().notes;
}

export function useIssueStore(): IssueStore {
  return useStores().issues;
}

export function useCycleStore(): CycleStore {
  return useStores().cycles;
}

export function useAIStore(): AIStore {
  return useStores().ai;
}

/** Hook to access the OnboardingStore from context. */
export function useOnboardingStore(): OnboardingStore {
  return useStores().onboarding;
}

/** Hook to access the RoleSkillStore from context. */
export function useRoleSkillStore(): RoleSkillStore {
  return useStores().roleSkill;
}

/** Hook to access the HomepageUIStore from context. */
export function useHomepageStore(): HomepageUIStore {
  return useStores().homepage;
}

/**
 * Convenient hook to access multiple stores at once.
 * Returns an object with named stores for destructuring.
 */
export function useStore() {
  const store = useStores();
  return {
    authStore: store.auth,
    uiStore: store.ui,
    workspaceStore: store.workspace,
    notificationStore: store.notifications,
    noteStore: store.notes,
    issueStore: store.issues,
    cycleStore: store.cycles,
    aiStore: store.ai,
    ai: store.ai, // Alias for consistency with task specs
    onboardingStore: store.onboarding,
    roleSkillStore: store.roleSkill,
    homepageStore: store.homepage,
  };
}
