/**
 * Homepage Hub Types - US-19
 * Types matching backend API response schemas from H008.
 */

// ---------------------------------------------------------------------------
// Activity Feed
// ---------------------------------------------------------------------------

/** Project reference embedded in activity cards */
export interface ActivityProject {
  id: string;
  name: string;
  identifier: string;
}

/** AI annotation preview on a note card */
export interface AnnotationPreview {
  type: 'suggestion' | 'warning' | 'issue_candidate';
  content: string;
  confidence: number;
}

/** Note activity card matching backend ActivityCardNote schema */
export interface ActivityCardNote {
  type: 'note';
  id: string;
  title: string;
  project: ActivityProject | null;
  topics?: string[];
  word_count: number;
  latest_annotation: AnnotationPreview | null;
  updated_at: string;
  is_pinned: boolean;
}

/** Assignee reference embedded in issue cards */
export interface ActivityAssignee {
  id: string;
  name: string;
  avatar_url: string | null;
}

/** Issue state reference embedded in issue cards */
export interface ActivityIssueState {
  name: string;
  color: string;
  group: string;
}

/** Issue priority levels */
export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

/** Issue activity card matching backend ActivityCardIssue schema */
export interface ActivityCardIssue {
  type: 'issue';
  id: string;
  identifier: string;
  title: string;
  project: ActivityProject | null;
  state: ActivityIssueState | null;
  priority: IssuePriority;
  assignee: ActivityAssignee | null;
  last_activity: string | null;
  updated_at: string;
}

/** Discriminated union of activity card types */
export type ActivityCard = ActivityCardNote | ActivityCardIssue;

/** Day group for activity feed rendering */
export interface DayGroup {
  label: string;
  date: string;
  items: ActivityCard[];
}

/** Pagination metadata for activity feed */
export interface ActivityMeta {
  total: number;
  cursor: string | null;
  has_more: boolean;
}

/** GET /homepage/activity response */
export interface HomepageActivityResponse {
  data: Record<string, ActivityCard[]>;
  meta: ActivityMeta;
}

// ---------------------------------------------------------------------------
// AI Digest
// ---------------------------------------------------------------------------

/** 12 digest suggestion categories from spec */
export type DigestCategory =
  | 'stale_issues'
  | 'missing_docs'
  | 'inconsistent_status'
  | 'blocked_deps'
  | 'unassigned_work'
  | 'overdue_cycles'
  | 'pr_review_pending'
  | 'duplicate_candidates'
  | 'note_refinement'
  | 'project_health'
  | 'knowledge_gaps'
  | 'release_readiness';

/** Action type for digest suggestion buttons */
export type DigestActionType = 'navigate' | 'quick_action';

/** Entity type referenced by a digest suggestion */
export type DigestEntityType = 'issue' | 'note' | 'cycle' | 'project' | 'pull_request';

/** Individual digest suggestion matching backend DigestSuggestion schema */
export interface DigestSuggestion {
  id: string;
  category: DigestCategory;
  title: string;
  description: string;
  entity_id: string | null;
  entity_type: DigestEntityType | null;
  entity_identifier?: string | null;
  project_id?: string | null;
  project_name?: string | null;
  action_type?: DigestActionType;
  action_label?: string;
  action_url: string | null;
  relevance_score: number;
}

/** Digest generation source */
export type DigestGeneratedBy = 'scheduled' | 'manual';

/** GET /homepage/digest response */
export interface DigestResponse {
  data: {
    generated_at: string;
    generated_by: DigestGeneratedBy;
    suggestions: DigestSuggestion[];
    suggestion_count: number;
  };
}

/** POST /homepage/digest/refresh response */
export interface DigestRefreshResponse {
  data: {
    status: 'generating' | 'completed' | 'error';
    estimated_seconds: number;
  };
}

// ---------------------------------------------------------------------------
// Payloads
// ---------------------------------------------------------------------------

/** POST /homepage/digest/dismiss payload */
export interface DismissSuggestionPayload {
  suggestion_id: string;
  category: DigestCategory;
  entity_id: string | null;
  entity_type: DigestEntityType | null;
}

/** POST /homepage/notes/from-chat payload */
export interface CreateNoteFromChatPayload {
  chat_session_id: string;
  title?: string;
  project_id?: string;
}

/** POST /homepage/notes/from-chat response */
export interface CreateNoteFromChatResponse {
  data: {
    note_id: string;
    title: string;
    source_chat_session_id: string;
  };
}

// ---------------------------------------------------------------------------
// UI State
// ---------------------------------------------------------------------------

/** Homepage zone identifiers for keyboard navigation (F6 cycling) */
export type HomepageZone = 'chat' | 'activity' | 'digest';
