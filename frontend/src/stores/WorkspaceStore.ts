'use client';

import { makeAutoObservable, runInAction, computed } from 'mobx';
import type {
  Workspace,
  WorkspaceRole,
  WorkspaceMember,
  CreateWorkspaceData,
  UpdateWorkspaceData,
  InviteMemberData,
  WorkspaceFeatureToggles,
} from '@/types';
import { DEFAULT_FEATURE_TOGGLES } from '@/types';
import type { AuthStore } from './AuthStore';
import { ApiError } from '@/services/api/client';

export type {
  WorkspaceRole,
  WorkspaceMember,
  CreateWorkspaceData,
  UpdateWorkspaceData,
  InviteMemberData,
};

interface WorkspaceApi {
  list(): Promise<{ items: Workspace[] }>;
  get(id: string): Promise<Workspace>;
  create(data: CreateWorkspaceData): Promise<Workspace>;
  update(id: string, data: UpdateWorkspaceData): Promise<Workspace>;
  delete(id: string): Promise<void>;
  getMembers(workspaceId: string): Promise<WorkspaceMember[]>;
  inviteMember(
    workspaceId: string,
    data: InviteMemberData
  ): Promise<WorkspaceMember | { invitation: true; id: string; email: string }>;
  removeMember(workspaceId: string, memberId: string): Promise<void>;
  updateMemberRole(
    workspaceId: string,
    memberId: string,
    role: WorkspaceRole
  ): Promise<WorkspaceMember>;
  getFeatureToggles(workspaceId: string): Promise<WorkspaceFeatureToggles>;
  updateFeatureToggles(
    workspaceId: string,
    data: Partial<WorkspaceFeatureToggles>
  ): Promise<WorkspaceFeatureToggles>;
}

export class WorkspaceStore {
  workspaces: Map<string, Workspace> = new Map();
  currentWorkspaceId: string | null = null;
  members: Map<string, WorkspaceMember[]> = new Map();
  featureToggles: WorkspaceFeatureToggles | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  private api: WorkspaceApi | null = null;
  private authStore: AuthStore | null = null;

  constructor() {
    makeAutoObservable(this, {
      currentWorkspace: computed,
      currentWorkspaceId: true,
      workspaceList: computed,
      currentMembers: computed,
      memberCount: computed,
      isAdmin: computed,
      isOwner: computed,
      currentUserRole: computed,
    });

    this.loadFromStorage();
  }

  setApi(api: WorkspaceApi): void {
    this.api = api;
  }

  setAuthStore(authStore: AuthStore): void {
    this.authStore = authStore;
  }

  get currentWorkspace(): Workspace | null {
    return this.currentWorkspaceId ? (this.workspaces.get(this.currentWorkspaceId) ?? null) : null;
  }

  get workspaceList(): Workspace[] {
    return Array.from(this.workspaces.values()).sort((a, b) => a.name.localeCompare(b.name));
  }

  get currentMembers(): WorkspaceMember[] {
    if (!this.currentWorkspaceId) return [];
    return this.members.get(this.currentWorkspaceId) || [];
  }

  get memberCount(): number {
    return this.currentMembers.length;
  }

  get currentUserRole(): WorkspaceRole | null {
    const userId = this.authStore?.user?.id;
    if (!userId || !this.currentWorkspaceId) return null;

    // Prefer membership data from /auth/me (always includes all pages)
    const memberships = this.authStore?.user?.workspaceMemberships;
    if (memberships && memberships.length > 0) {
      const membership = memberships.find((m) => m.workspaceId === this.currentWorkspaceId);
      if (membership) {
        return membership.role.toLowerCase() as WorkspaceRole;
      }
    }

    // Fallback: derive from paginated member list (may miss current user if not on page 1)
    const members = this.members.get(this.currentWorkspaceId);
    if (!members) return null;
    const member = members.find((m) => m.userId === userId);
    if (!member) return null;
    // Normalize to lowercase — backend returns UPPERCASE after migration 066
    return member.role.toLowerCase() as WorkspaceRole;
  }

  get isAdmin(): boolean {
    const role = this.currentUserRole;
    return role === 'admin' || role === 'owner';
  }

  get isOwner(): boolean {
    return this.currentUserRole === 'owner';
  }

  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const storedWorkspaceId = localStorage.getItem('pilot-space:current-workspace');
      if (storedWorkspaceId) {
        this.currentWorkspaceId = storedWorkspaceId;
      }
    } catch {
      // Ignore localStorage errors (SSR, privacy mode)
    }
  }

  private saveToStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      if (this.currentWorkspaceId) {
        localStorage.setItem('pilot-space:current-workspace', this.currentWorkspaceId);
      } else {
        localStorage.removeItem('pilot-space:current-workspace');
      }
    } catch {
      // Ignore localStorage errors
    }
  }

  selectWorkspace(workspaceId: string | null): void {
    this.currentWorkspaceId = workspaceId;
    this.saveToStorage();

    if (workspaceId && !this.members.has(workspaceId)) {
      this.fetchMembers(workspaceId);
    }
    if (workspaceId) {
      this.loadFeatureToggles(workspaceId);
    } else {
      this.featureToggles = null;
    }
  }

  /**
   * Sets the current workspace directly (skipping fetch).
   * Used by WorkspaceGuard to sync workspace from context to MobX store.
   */
  setCurrentWorkspace(workspace: Workspace): void {
    this.workspaces.set(workspace.id, workspace);
    this.currentWorkspaceId = workspace.id;
    this.saveToStorage();

    if (!this.members.has(workspace.id)) {
      this.fetchMembers(workspace.id);
    }
    this.loadFeatureToggles(workspace.id);
  }

  async fetchWorkspaces(options?: { ensureSelection?: boolean }): Promise<void> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return;
    }

    const ensureSelection = options?.ensureSelection ?? false;

    this.isLoading = true;
    this.error = null;

    try {
      const response = await this.api.list();

      runInAction(() => {
        this.workspaces.clear();
        for (const ws of response.items) {
          this.workspaces.set(ws.id, ws);
        }

        if (ensureSelection) {
          const firstWorkspace = response.items[0];
          if (!this.currentWorkspaceId && firstWorkspace) {
            this.selectWorkspace(firstWorkspace.id);
          }

          if (
            this.currentWorkspaceId &&
            !this.workspaces.has(this.currentWorkspaceId) &&
            firstWorkspace
          ) {
            this.selectWorkspace(firstWorkspace.id);
          }
        }

        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to fetch workspaces';
        this.isLoading = false;
      });
    }
  }

  async fetchWorkspace(workspaceId: string): Promise<Workspace | null> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return null;
    }

    this.isLoading = true;
    this.error = null;

    try {
      const workspace = await this.api.get(workspaceId);

      runInAction(() => {
        this.workspaces.set(workspace.id, workspace);
        this.isLoading = false;
      });

      return workspace;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to fetch workspace';
        this.isLoading = false;
      });
      return null;
    }
  }

  async createWorkspace(data: CreateWorkspaceData): Promise<Workspace | null> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const workspace = await this.api.create(data);

      runInAction(() => {
        this.workspaces.set(workspace.id, workspace);
        this.selectWorkspace(workspace.id);
        this.isSaving = false;
      });

      return workspace;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to create workspace';
        this.isSaving = false;
      });
      return null;
    }
  }

  async updateWorkspace(workspaceId: string, data: UpdateWorkspaceData): Promise<Workspace | null> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const workspace = await this.api.update(workspaceId, data);

      runInAction(() => {
        this.workspaces.set(workspace.id, workspace);
        this.isSaving = false;
      });

      return workspace;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update workspace';
        this.isSaving = false;
      });
      return null;
    }
  }

  async deleteWorkspace(workspaceId: string): Promise<boolean> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return false;
    }

    this.isSaving = true;
    this.error = null;

    try {
      await this.api.delete(workspaceId);

      runInAction(() => {
        this.workspaces.delete(workspaceId);
        this.members.delete(workspaceId);

        if (this.currentWorkspaceId === workspaceId) {
          const remaining = this.workspaceList;
          const firstRemaining = remaining[0];
          this.selectWorkspace(firstRemaining ? firstRemaining.id : null);
        }

        this.isSaving = false;
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to delete workspace';
        this.isSaving = false;
      });
      return false;
    }
  }

  async fetchMembers(workspaceId: string): Promise<void> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return;
    }

    try {
      const members = await this.api.getMembers(workspaceId);

      runInAction(() => {
        this.members.set(workspaceId, members);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to fetch members';
      });
    }
  }

  async inviteMember(
    workspaceId: string,
    data: InviteMemberData
  ): Promise<WorkspaceMember | { invitation: true; id: string; email: string } | null> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const result = await this.api.inviteMember(workspaceId, data);

      runInAction(() => {
        // Only add to members list if user was added immediately (not a pending invitation)
        if (!('invitation' in result)) {
          const currentMembers = this.members.get(workspaceId) || [];
          this.members.set(workspaceId, [...currentMembers, result]);
        }
        this.isSaving = false;
      });

      return result;
    } catch (err) {
      runInAction(() => {
        if (err instanceof ApiError && err.status === 409) {
          this.error = 'conflict:already_member_or_invited';
        } else {
          this.error = err instanceof Error ? err.message : 'Failed to invite member';
        }
        this.isSaving = false;
      });
      return null;
    }
  }

  async removeMember(workspaceId: string, memberId: string): Promise<boolean> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return false;
    }

    this.isSaving = true;
    this.error = null;

    try {
      await this.api.removeMember(workspaceId, memberId);

      runInAction(() => {
        const currentMembers = this.members.get(workspaceId) || [];
        this.members.set(
          workspaceId,
          currentMembers.filter((m) => m.userId !== memberId)
        );
        this.isSaving = false;
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to remove member';
        this.isSaving = false;
      });
      return false;
    }
  }

  async updateMemberRole(
    workspaceId: string,
    memberId: string,
    role: WorkspaceRole
  ): Promise<WorkspaceMember | null> {
    if (!this.api) {
      this.error = 'Workspace API not initialized';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const updatedMember = await this.api.updateMemberRole(workspaceId, memberId, role);

      runInAction(() => {
        const currentMembers = this.members.get(workspaceId) || [];
        const index = currentMembers.findIndex((m) => m.id === memberId);
        if (index !== -1) {
          currentMembers[index] = updatedMember;
          this.members.set(workspaceId, [...currentMembers]);
        }
        this.isSaving = false;
      });

      return updatedMember;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update member role';
        this.isSaving = false;
      });
      return null;
    }
  }

  /**
   * Check if a workspace feature is enabled.
   * Falls back to defaults when toggles haven't loaded yet.
   */
  isFeatureEnabled(key: keyof WorkspaceFeatureToggles): boolean {
    if (this.featureToggles) {
      return this.featureToggles[key] ?? DEFAULT_FEATURE_TOGGLES[key];
    }
    return DEFAULT_FEATURE_TOGGLES[key];
  }

  async loadFeatureToggles(workspaceId: string): Promise<void> {
    if (!this.api) return;

    try {
      const toggles = await this.api.getFeatureToggles(workspaceId);
      runInAction(() => {
        this.featureToggles = toggles;
        this.error = null;
      });
    } catch (err) {
      // Surface the error so the UI can display it, then fall back to defaults
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load feature toggles';
        this.featureToggles = { ...DEFAULT_FEATURE_TOGGLES };
      });
    }
  }

  async saveFeatureToggles(data: Partial<WorkspaceFeatureToggles>): Promise<boolean> {
    if (!this.api || !this.currentWorkspaceId) return false;

    this.isSaving = true;
    this.error = null;

    try {
      const updated = await this.api.updateFeatureToggles(this.currentWorkspaceId, data);
      runInAction(() => {
        this.featureToggles = updated;
        this.isSaving = false;
      });
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update feature toggles';
        this.isSaving = false;
      });
      return false;
    }
  }

  getWorkspaceBySlug(slug: string): Workspace | undefined {
    return this.workspaceList.find((w) => w.slug === slug);
  }

  clearError(): void {
    this.error = null;
  }

  reset(): void {
    this.workspaces.clear();
    this.currentWorkspaceId = null;
    this.members.clear();
    this.featureToggles = null;
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.saveToStorage();
  }
}

export const workspaceStore = new WorkspaceStore();
