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
import { TaskStore } from '@/stores/TaskStore';
import { IssueViewStore } from './features/issues/IssueViewStore';
import { ArtifactStore } from './features/artifacts/ArtifactStore';
import { FileStore } from '@/features/code/stores/FileStore';
import { GitStore } from '@/features/code/stores/GitStore';
import { workspacesApi } from '@/services/api/workspaces';

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
  tasks: TaskStore;
  issueView: IssueViewStore;
  artifacts: ArtifactStore;
  files: FileStore;
  git: GitStore;

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
    this.tasks = new TaskStore();
    this.issueView = new IssueViewStore();
    this.artifacts = new ArtifactStore();
    this.files = new FileStore();
    this.git = new GitStore();

    // Wire cross-store references
    this.workspace.setAuthStore(this.auth);
    this.workspace.setApi(workspacesApi);
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
    this.tasks.reset();
    this.issueView.reset();
    this.artifacts.reset();
    this.files.reset();
    this.git.reset();
  }

  dispose(): void {
    this.auth.dispose();
    this.ui.dispose();
    this.onboarding.dispose();
    this.issueView.dispose();
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

/** Hook to access the TaskStore from context. */
export function useTaskStore(): TaskStore {
  return useStores().tasks;
}

/** Hook to access the IssueViewStore from context. */
export function useIssueViewStore(): IssueViewStore {
  return useStores().issueView;
}

/** Hook to access the ArtifactStore from context. */
export function useArtifactStore(): ArtifactStore {
  return useStores().artifacts;
}

/** Hook to access the FileStore from context. */
export function useFileStore(): FileStore {
  return useStores().files;
}

/** Hook to access the GitStore from context. */
export function useGitStore(): GitStore {
  return useStores().git;
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
    taskStore: store.tasks,
    issueViewStore: store.issueView,
  };
}
