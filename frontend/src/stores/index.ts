// Root Store
export {
  RootStore,
  rootStore,
  StoreContext,
  useStores,
  useStore,
  useAuthStore,
  useUIStore,
  useWorkspaceStore,
  useNotificationStore,
  useNoteStore,
  useIssueStore,
  useIssueViewStore,
  useAIStore,
  useTaskStore,
  useArtifactStore,
  useArtifactPanelStore,
} from './RootStore';

// Auth Store
export { AuthStore, authStore, type AuthUser, type WorkspaceMembership } from './AuthStore';

// UI Store
export { UIStore, uiStore, type Theme, type ModalState, type Toast } from './UIStore';

// Workspace Store
export {
  WorkspaceStore,
  workspaceStore,
  type WorkspaceRole,
  type WorkspaceMember,
  type CreateWorkspaceData,
  type UpdateWorkspaceData,
  type InviteMemberData,
} from './WorkspaceStore';

// Notification Store
export {
  NotificationStore,
  notificationStore,
  type Notification,
  type NotificationPriority,
  type NotificationType,
} from './NotificationStore';

// Feature Stores
export { NoteStore, noteStore } from './features/notes/NoteStore';
export { IssueStore, issueStore } from './features/issues/IssueStore';
export { IssueViewStore, issueViewStore } from './features/issues/IssueViewStore';
export { TaskStore } from './TaskStore';
export { ArtifactStore } from './features/artifacts/ArtifactStore';
export { ArtifactPanelStore } from './ArtifactPanelStore';
export type { ArtifactTab, LayoutMode } from './ArtifactPanelStore';

// AI Stores
export {
  AIStore,
  aiStore,
  getAIStore,
  GhostTextStore,
  AIContextStore,
  ApprovalStore,
  AISettingsStore,
} from './ai';
export type { AIContextPhase, AIContextResult } from './ai';
