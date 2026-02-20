// Workspace Types
export type WorkspaceRole = 'owner' | 'admin' | 'member' | 'guest';

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  ownerId: string;
  owner?: User;
  memberIds: string[];
  members?: User[];
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceMember {
  id: string;
  userId: string;
  user: User;
  workspaceId: string;
  role: WorkspaceRole;
  joinedAt: string;
  weeklyAvailableHours: number;
}

export interface CreateWorkspaceData {
  name: string;
  slug?: string;
  description?: string;
}

export interface UpdateWorkspaceData {
  name?: string;
  slug?: string;
  description?: string;
}

export interface InviteMemberData {
  email: string;
  role: WorkspaceRole;
}

// User Types
export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  createdAt?: string;
  updatedAt?: string;
}

// User Brief (matches backend UserBriefSchema)
export interface UserBrief {
  id: string;
  email: string;
  displayName: string | null;
}

// State Brief (matches backend StateBriefSchema)
export type StateGroup = 'backlog' | 'unstarted' | 'started' | 'completed' | 'cancelled';

export interface StateBrief {
  id: string;
  name: string;
  color: string;
  group: StateGroup;
}

// Label Types
export interface Label {
  id: string;
  name: string;
  color: string;
  projectId: string;
}

// Label Brief (matches backend LabelBriefSchema)
export interface LabelBrief {
  id: string;
  name: string;
  color: string;
}

// Project Types
export interface ProjectBrief {
  id: string;
  name: string;
  identifier: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  identifier: string;
  slug?: string;
  workspaceId: string;
  leadId?: string;
  lead?: { id: string; email: string; displayName?: string | null };
  icon?: string;
  memberIds?: string[];
  members?: User[];
  issueCount: number;
  openIssueCount: number;
  completedIssueCount?: number;
  createdAt: string;
  updatedAt: string;
}

// Issue Priority (shared across issue and cycle domains)
export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';
