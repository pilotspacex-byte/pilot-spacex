/**
 * Homepage Hub Feature - US-19
 * Two-panel layout: DailyBrief + ChatView command center
 */

// Types
export type {
  ActivityCardNote,
  ActivityCardIssue,
  ActivityCard,
  ActivityProject,
  ActivityAssignee,
  ActivityIssueState,
  AnnotationPreview,
  IssuePriority,
  DayGroup,
  ActivityMeta,
  HomepageActivityResponse,
} from './types';

// API client
export { homepageApi } from './api/homepage-api';

// Constants
export { ITEMS_PER_PAGE, ACTIVITY_STALE_TIME } from './constants';

// Components
export { HomepageHub } from './components/HomepageHub';
