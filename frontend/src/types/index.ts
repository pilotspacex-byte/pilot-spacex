/**
 * Types barrel - re-exports all domain types for backward-compatible imports.
 * Domain types are organized in separate files:
 *   - workspace.ts  → Workspace, User, Project, StateBrief, etc.
 *   - issue.ts      → Issue, LinkedIssueBrief, Activity, etc.
 *   - note.ts       → Note, NoteAnnotation, NoteNoteLink, etc.
 *   - cycle.ts      → Cycle, CycleMetrics, BurndownChartData, etc.
 *   - ai.ts         → AIContext, Task, GhostTextSuggestion, etc.
 *   - approval.ts   → PendingApproval, ApprovalStatus, etc.
 */
export type {
  // Workspace domain
  WorkspaceRole,
  Workspace,
  WorkspaceMember,
  CreateWorkspaceData,
  UpdateWorkspaceData,
  InviteMemberData,
  User,
  UserBrief,
  StateGroup,
  StateBrief,
  Label,
  LabelBrief,
  ProjectBrief,
  Project,
  IssuePriority,
  WorkspaceFeatureToggles,
} from './workspace';

export { DEFAULT_FEATURE_TOGGLES } from './workspace';

export type {
  // Issue domain
  IssueState,
  IssueType,
  Issue,
  CreateIssueData,
  UpdateIssueData,
  IssueBrief,
  LinkedIssueBrief,
  Activity,
  ActivityTimelineResponse,
  IntegrationLink,
  IssueRelation,
  NoteIssueLink,
  NoteLinkType,
  RelatedSuggestion,
} from './issue';

export { VALID_NOTE_LINK_TYPES } from './issue';

export type {
  // Note domain
  JSONContent,
  Note,
  NoteContent,
  NoteBlock,
  AnnotationType,
  AnnotationStatus,
  AnnotationMetadata,
  NoteAnnotation,
  CreateNoteData,
  UpdateNoteData,
  NoteNoteLink,
  NoteBacklink,
  NoteLinkSearchResult,
} from './note';

export type {
  // Cycle domain
  CycleStatus,
  Cycle,
  CycleMetrics,
  CreateCycleData,
  UpdateCycleData,
  RolloverCycleData,
  RolloverCycleResult,
  BurndownDataPoint,
  BurndownChartData,
  VelocityDataPoint,
  VelocityChartData,
} from './cycle';

export type {
  // AI domain
  AIContext,
  CodeReference,
  SuggestedTask,
  TaskStatus,
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
  SubtaskSchema,
  DecomposeResponse,
  ContextExportResponse,
  GhostTextSuggestion,
} from './ai';

export type {
  // Approval domain
  ApprovalStatus,
  ApprovalActionType,
  ApprovalUrgency,
  PendingApproval,
  CreateApprovalRequest,
  ApprovalResolution,
} from './approval';

export type {
  // Attachment domain
  AttachmentStatus,
  AttachmentSource,
  AttachmentMetadata,
  AttachmentContext,
  AttachmentUploadResponse,
} from './attachments';
export { ACCEPTED_MIME_TYPES, FILE_SIZE_LIMITS } from './attachments';
