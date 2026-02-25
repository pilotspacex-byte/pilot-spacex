import type {
  UserBrief,
  StateBrief,
  IssuePriority,
  ProjectBrief,
  LabelBrief,
  User,
} from './workspace';

export type IssueState = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';

export type IssueType = 'bug' | 'feature' | 'improvement' | 'task';

export interface Issue {
  id: string;
  identifier: string;
  name: string;
  /** @deprecated Use `name` instead. Present for backward compatibility. */
  title?: string;
  description?: string;
  descriptionHtml?: string;
  state: StateBrief;
  priority: IssuePriority;
  type?: IssueType;
  projectId: string;
  workspaceId: string;
  sequenceId: number;
  sortOrder: number;
  assigneeId?: string;
  assignee?: UserBrief | null;
  reporterId: string;
  reporter: UserBrief;
  labels: LabelBrief[];
  estimatePoints?: number;
  /** Time estimate in hours (0.5 increments, T-245) */
  estimateHours?: number;
  startDate?: string;
  targetDate?: string;
  cycleId?: string;
  parentId?: string;
  subIssueCount: number;
  project: ProjectBrief;
  aiGenerated?: boolean;
  hasAiEnhancements: boolean;
  aiMetadata?: Record<string, unknown>;
  acceptanceCriteria?: string[];
  technicalRequirements?: string;
  createdAt: string;
  updatedAt: string;
  noteLinks?: NoteIssueLink[];
}

export interface CreateIssueData {
  name: string;
  description?: string;
  descriptionHtml?: string;
  projectId?: string;
  stateId?: string;
  priority?: IssuePriority;
  type?: IssueType;
  assigneeId?: string;
  labelIds?: string[];
  estimatePoints?: number;
  startDate?: string;
  targetDate?: string;
  cycleId?: string;
  moduleId?: string;
  parentId?: string;
}

export interface UpdateIssueData {
  name?: string;
  description?: string;
  descriptionHtml?: string;
  priority?: IssuePriority;
  stateId?: string;
  assigneeId?: string;
  cycleId?: string;
  moduleId?: string;
  parentId?: string;
  estimatePoints?: number;
  /** Time estimate in hours (0.5 increments, 0-9999.9, T-245) */
  estimateHours?: number;
  startDate?: string;
  targetDate?: string;
  sortOrder?: number;
  labelIds?: string[];
  acceptanceCriteria?: string[];
  technicalRequirements?: string;
  clearAssignee?: boolean;
  clearCycle?: boolean;
  clearModule?: boolean;
  clearParent?: boolean;
  clearEstimate?: boolean;
  clearStartDate?: boolean;
  clearTargetDate?: boolean;
}

export interface IssueBrief {
  id: string;
  identifier: string;
  name: string;
  priority: IssuePriority;
  state?: StateBrief;
  assignee?: UserBrief;
}

// Linked Issue Brief (matches backend IssueBriefResponse in note detail)
export interface LinkedIssueBrief {
  id: string;
  identifier: string;
  name: string;
  priority: IssuePriority;
  state: StateBrief;
  assignee?: UserBrief | null;
  /** Block ID where the issue is linked (from NoteIssueLink.block_id) */
  blockId?: string;
}

// Activity (matches backend ActivityResponse)
export interface Activity {
  id: string;
  activityType: string;
  field: string | null;
  oldValue: string | null;
  newValue: string | null;
  comment: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
  actor: UserBrief | null;
}

// Activity Timeline Response (matches backend ActivityTimelineResponse)
export interface ActivityTimelineResponse {
  activities: Activity[];
  total: number;
}

// Integration Link (frontend-only, for future backend support)
export interface IntegrationLink {
  id: string;
  issueId: string;
  integrationType: 'github_pr' | 'github_issue' | 'slack';
  externalId: string;
  externalUrl: string;
  prNumber?: number;
  prTitle?: string;
  prStatus?: 'open' | 'merged' | 'closed';
}

// Note Issue Link (frontend-only, for future backend support)
export interface NoteIssueLink {
  id: string;
  noteId: string;
  issueId: string;
  linkType: 'CREATED' | 'EXTRACTED' | 'REFERENCED';
  noteTitle: string;
}

export type { UserBrief, StateBrief, ProjectBrief, LabelBrief, User, IssuePriority };
