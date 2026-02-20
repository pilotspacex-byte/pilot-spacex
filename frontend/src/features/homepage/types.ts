/**
 * Homepage Hub Types - US-19
 * Types matching backend API response schemas from H008.
 * Backend uses BaseSchema with alias_generator=to_camel, so all response
 * fields arrive as camelCase in JSON.
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

/** Note activity card (camelCase from BaseSchema serialization) */
export interface ActivityCardNote {
  type: 'note';
  id: string;
  title: string;
  project: ActivityProject | null;
  topics?: string[];
  wordCount: number;
  latestAnnotation: AnnotationPreview | null;
  updatedAt: string;
  isPinned: boolean;
}

/** Assignee reference embedded in issue cards */
export interface ActivityAssignee {
  id: string;
  name: string;
  avatarUrl: string | null;
}

/** Issue state reference embedded in issue cards */
export interface ActivityIssueState {
  name: string;
  color: string;
  group: string;
}

/** Issue priority levels */
export type IssuePriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

/** Issue activity card (camelCase from BaseSchema serialization) */
export interface ActivityCardIssue {
  type: 'issue';
  id: string;
  identifier: string;
  title: string;
  project: ActivityProject | null;
  state: ActivityIssueState | null;
  priority: IssuePriority;
  assignee: ActivityAssignee | null;
  lastActivity: string | null;
  updatedAt: string;
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
  hasMore: boolean;
}

/** GET /homepage/activity response */
export interface HomepageActivityResponse {
  data: Record<string, ActivityCard[]>;
  meta: ActivityMeta;
}

// ---------------------------------------------------------------------------
// AI Digest
// ---------------------------------------------------------------------------

/** Digest suggestion category values */
export type DigestCategory =
  | 'stale_issues'
  | 'unlinked_notes'
  | 'cycle_risk'
  | 'blocked_dependencies'
  | 'overdue_items'
  | 'unassigned_priority';

/** Single AI digest suggestion (camelCase from BaseSchema serialization) */
export interface DigestSuggestion {
  id: string;
  category: DigestCategory;
  title: string;
  description: string;
  entityId: string | null;
  entityType: string | null;
  entityIdentifier: string | null;
  projectId: string | null;
  projectName: string | null;
  actionType: string | null;
  actionLabel: string | null;
  actionUrl: string | null;
  relevanceScore: number;
}

/** Digest data payload (camelCase from BaseSchema serialization) */
export interface DigestData {
  generatedAt: string;
  generatedBy: string;
  suggestions: DigestSuggestion[];
  suggestionCount: number;
}

/** GET /homepage/digest response */
export interface DigestResponse {
  data: DigestData;
}

/** POST /homepage/digest/refresh response */
export interface DigestRefreshResponse {
  data: {
    status: string;
    estimatedSeconds: number;
  };
}

/** POST /homepage/digest/dismiss request body */
export interface DigestDismissPayload {
  suggestionId: string;
  entityId: string | null;
  entityType: string | null;
  category: string;
}
