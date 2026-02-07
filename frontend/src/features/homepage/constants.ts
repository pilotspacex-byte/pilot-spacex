/**
 * Homepage Hub Constants - US-19
 * Static configuration for activity feed, digest panel, and compact chat.
 */

import type { DigestCategory } from './types';

// ---------------------------------------------------------------------------
// Activity Feed
// ---------------------------------------------------------------------------

/** Number of activity cards per page (infinite scroll) */
export const ITEMS_PER_PAGE = 20;

/** TanStack Query stale time for activity feed (30 seconds) */
export const ACTIVITY_STALE_TIME = 30_000;

/** Maximum characters for annotation preview text */
export const MAX_ANNOTATION_PREVIEW_LENGTH = 80;

/** Day group label keys matching backend response buckets */
export const DAY_GROUP_LABELS = {
  today: 'Today',
  yesterday: 'Yesterday',
  this_week: 'This Week',
} as const;

/** Ordered day group keys for rendering */
export const DAY_GROUP_ORDER = ['today', 'yesterday', 'this_week'] as const;

// ---------------------------------------------------------------------------
// AI Digest
// ---------------------------------------------------------------------------

/** TanStack Query stale time for digest (5 minutes) */
export const DIGEST_STALE_TIME = 300_000;

/** Human-readable labels for digest categories */
export const DIGEST_CATEGORY_LABELS: Record<DigestCategory, string> = {
  stale_issues: 'Stale Issues',
  missing_docs: 'Missing Documentation',
  inconsistent_status: 'Inconsistent Status',
  blocked_deps: 'Blocked Dependencies',
  unassigned_work: 'Unassigned Work',
  overdue_cycles: 'Overdue Cycle Items',
  pr_review_pending: 'PR Review Pending',
  duplicate_candidates: 'Duplicate Candidates',
  note_refinement: 'Note Refinement',
  project_health: 'Project Health',
  knowledge_gaps: 'Knowledge Gaps',
  release_readiness: 'Release Readiness',
};

// ---------------------------------------------------------------------------
// Compact ChatView
// ---------------------------------------------------------------------------

/** Maximum expanded height for compact chat panel (px) */
export const CHAT_MAX_HEIGHT = 400;

/** Breakpoint below which chat renders as mobile bottom sheet (px) */
export const CHAT_MOBILE_BREAKPOINT = 768;

/** Animation duration for chat expand/collapse (ms) */
export const CHAT_ANIMATION_DURATION = 200;
