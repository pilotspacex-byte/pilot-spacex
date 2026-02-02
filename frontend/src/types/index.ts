// Issue Types
export type IssueState = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';

export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

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
  startDate?: string;
  targetDate?: string;
  cycleId?: string;
  parentId?: string;
  subIssueCount: number;
  project: ProjectBrief;
  aiGenerated?: boolean;
  hasAiEnhancements: boolean;
  aiMetadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
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
  startDate?: string;
  targetDate?: string;
  sortOrder?: number;
  labelIds?: string[];
  clearAssignee?: boolean;
  clearCycle?: boolean;
  clearModule?: boolean;
  clearParent?: boolean;
  clearEstimate?: boolean;
  clearStartDate?: boolean;
  clearTargetDate?: boolean;
}

// Note Types

/**
 * TipTap/ProseMirror JSON content structure
 */
export interface JSONContent {
  type?: string;
  attrs?: Record<string, unknown>;
  content?: JSONContent[];
  marks?: { type: string; attrs?: Record<string, unknown> }[];
  text?: string;
}

/**
 * Note entity - primary document for Note-First workflow
 */
export interface Note {
  id: string;
  title: string;
  content: JSONContent;
  summary?: string;
  wordCount: number;
  readingTimeMins: number;
  isPinned: boolean;
  /** Whether note contains AI-assisted edits (per UI Spec v3.3) */
  isAIAssisted?: boolean;
  projectId?: string;
  templateId?: string;
  ownerId: string;
  workspaceId: string;
  owner?: User;
  collaborators: User[];
  linkedIssues: Issue[];
  annotations: NoteAnnotation[];
  topics: string[];
  createdAt: string;
  updatedAt: string;
}

/**
 * @deprecated Use JSONContent instead
 */
export interface NoteContent {
  type: 'doc';
  content: NoteBlock[];
}

/**
 * @deprecated Use JSONContent instead
 */
export interface NoteBlock {
  id: string;
  type: string;
  content?: unknown;
  attrs?: Record<string, unknown>;
}

/**
 * Annotation type for AI-generated suggestions
 */
export type AnnotationType =
  | 'suggestion'
  | 'warning'
  | 'issue_candidate'
  | 'info'
  | 'question'
  | 'insight'
  | 'reference';

/**
 * Annotation status for tracking user actions
 */
export type AnnotationStatus = 'pending' | 'accepted' | 'rejected' | 'dismissed';

/**
 * AI annotation metadata
 */
export interface AnnotationMetadata {
  title?: string;
  summary?: string;
  suggestedText?: string;
  references?: Array<{ title: string; url: string }>;
}

/**
 * AI annotation on a note block
 */
export interface NoteAnnotation {
  id: string;
  noteId: string;
  blockId: string;
  content: string;
  type: AnnotationType;
  confidence: number;
  status: AnnotationStatus;
  aiMetadata?: AnnotationMetadata;
  createdAt: string;
  updatedAt?: string;
  /** @deprecated Use status instead */
  resolved?: boolean;
}

export interface CreateNoteData {
  title: string;
  content?: JSONContent;
  workspaceId: string;
  projectId?: string;
  templateId?: string;
}

export interface UpdateNoteData {
  title?: string;
  content?: JSONContent;
  projectId?: string;
  isPinned?: boolean;
}

// Project Types
export interface Project {
  id: string;
  name: string;
  description?: string;
  slug: string;
  workspaceId: string;
  leadId?: string;
  lead?: User;
  memberIds: string[];
  members?: User[];
  issueCount: number;
  completedIssueCount: number;
  createdAt: string;
  updatedAt: string;
}

// Workspace Types
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

// User Types
export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  createdAt: string;
  updatedAt: string;
}

// Label Types
export interface Label {
  id: string;
  name: string;
  color: string;
  projectId: string;
}

// State Brief (matches backend StateBriefSchema)
export type StateGroup = 'backlog' | 'unstarted' | 'started' | 'completed' | 'cancelled';

export interface StateBrief {
  id: string;
  name: string;
  color: string;
  group: StateGroup;
}

// User Brief (matches backend UserBriefSchema)
export interface UserBrief {
  id: string;
  email: string;
  displayName: string | null;
}

// Label Brief (matches backend LabelBriefSchema)
export interface LabelBrief {
  id: string;
  name: string;
  color: string;
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

// AI Types
export interface AIContext {
  issueId: string;
  relatedDocs: string[];
  codeReferences: CodeReference[];
  suggestedTasks: SuggestedTask[];
  claudeCodePrompts: string[];
}

export interface CodeReference {
  filePath: string;
  lineStart: number;
  lineEnd: number;
  content: string;
  relevance: number;
}

export interface SuggestedTask {
  title: string;
  description: string;
  estimatedHours?: number;
  priority: IssuePriority;
}

// Ghost Text Types
export interface GhostTextSuggestion {
  text: string;
  cursorPosition: number;
  confidence: number;
}

// Cycle Types (US-04 Sprint Planning)
export type CycleStatus = 'draft' | 'planned' | 'active' | 'completed' | 'cancelled';

export interface Cycle {
  id: string;
  workspaceId: string;
  name: string;
  description?: string;
  status: CycleStatus;
  startDate?: string;
  endDate?: string;
  sequence: number;
  createdAt: string;
  updatedAt: string;
  project: ProjectBrief;
  ownedBy?: User;
  metrics?: CycleMetrics;
  issueCount: number;
}

export interface ProjectBrief {
  id: string;
  name: string;
  identifier: string;
}

export interface CycleMetrics {
  cycleId: string;
  totalIssues: number;
  completedIssues: number;
  inProgressIssues: number;
  notStartedIssues: number;
  totalPoints: number;
  completedPoints: number;
  completionPercentage: number;
  velocity: number;
}

export interface CreateCycleData {
  name: string;
  description?: string;
  projectId: string;
  startDate?: string;
  endDate?: string;
  ownedById?: string;
  status?: CycleStatus;
}

export interface UpdateCycleData {
  name?: string;
  description?: string;
  startDate?: string;
  endDate?: string;
  status?: CycleStatus;
  ownedById?: string;
  clearDescription?: boolean;
  clearStartDate?: boolean;
  clearEndDate?: boolean;
  clearOwner?: boolean;
}

export interface RolloverCycleData {
  targetCycleId: string;
  issueIds?: string[];
  includeInProgress?: boolean;
  completeSourceCycle?: boolean;
}

export interface RolloverCycleResult {
  sourceCycle: Cycle;
  targetCycle: Cycle;
  rolledOverIssues: IssueBrief[];
  skippedCount: number;
  totalRolledOver: number;
}

export interface IssueBrief {
  id: string;
  identifier: string;
  name: string;
  priority: IssuePriority;
  state?: unknown;
  assignee?: User;
}

// Burndown Chart Types
export interface BurndownDataPoint {
  date: string;
  remainingPoints: number;
  remainingIssues: number;
  idealPoints: number;
  idealIssues: number;
}

export interface BurndownChartData {
  cycleId: string;
  startDate: string;
  endDate: string;
  totalPoints: number;
  totalIssues: number;
  dataPoints: BurndownDataPoint[];
}

// Velocity Chart Types
export interface VelocityDataPoint {
  cycleId: string;
  cycleName: string;
  completedPoints: number;
  committedPoints: number;
  velocity: number;
}

export interface VelocityChartData {
  projectId: string;
  dataPoints: VelocityDataPoint[];
  averageVelocity: number;
}

// ============================================================================
// Approval Types (Human-in-the-Loop per DD-003)
// ============================================================================

/**
 * Status of a pending approval.
 */
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

/**
 * Action types that require human approval per DD-003.
 */
export type ApprovalActionType =
  | 'issue_delete_bulk'
  | 'issue_merge_duplicate'
  | 'ai_bulk_update'
  | 'ai_create_sub_issues'
  | 'ai_archive_issues'
  | 'cycle_delete'
  | 'module_delete';

/**
 * Urgency level for approval requests.
 */
export type ApprovalUrgency = 'low' | 'medium' | 'high' | 'critical';

/**
 * Pending approval request requiring human confirmation.
 */
export interface PendingApproval {
  id: string;
  workspaceId: string;
  requestedById: string;
  requestedBy?: User;
  actionType: ApprovalActionType;
  actionDescription: string;
  consequences: string;
  urgency: ApprovalUrgency;
  status: ApprovalStatus;
  metadata?: Record<string, unknown>;
  affectedEntityIds: string[];
  affectedEntityType: 'issue' | 'cycle' | 'module' | 'note';
  expiresAt: string;
  createdAt: string;
  resolvedAt?: string;
  resolvedById?: string;
  resolvedBy?: User;
  resolutionNote?: string;
}

/**
 * Request payload for creating an approval.
 */
export interface CreateApprovalRequest {
  actionType: ApprovalActionType;
  actionDescription: string;
  consequences: string;
  urgency?: ApprovalUrgency;
  metadata?: Record<string, unknown>;
  affectedEntityIds: string[];
  affectedEntityType: 'issue' | 'cycle' | 'module' | 'note';
}

/**
 * Response after resolving an approval.
 */
export interface ApprovalResolution {
  approval: PendingApproval;
  actionExecuted: boolean;
  executionResult?: unknown;
  error?: string;
}
