/**
 * Homepage Hub Constants - US-19
 * Static configuration for the homepage activity feed.
 */

// ---------------------------------------------------------------------------
// Activity Feed
// ---------------------------------------------------------------------------

/** Number of activity cards per page (infinite scroll) */
export const ITEMS_PER_PAGE = 20;

/** TanStack Query stale time for activity feed (30 seconds) */
export const ACTIVITY_STALE_TIME = 30_000;

/** Maximum characters for annotation preview text */
export const MAX_ANNOTATION_PREVIEW_LENGTH = 80;

/** Maximum number of items to render in the activity feed (performance guard) */
export const MAX_RENDERED_ACTIVITY_ITEMS = 200;

/** Day group label keys matching backend response buckets (camelCase from BaseSchema alias_generator) */
export const DAY_GROUP_LABELS = {
  today: 'Today',
  yesterday: 'Yesterday',
  thisWeek: 'This Week',
} as const;

/** Ordered day group keys for rendering */
export const DAY_GROUP_ORDER = ['today', 'yesterday', 'thisWeek'] as const;
