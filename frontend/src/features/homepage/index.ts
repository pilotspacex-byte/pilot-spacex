/**
 * Homepage Hub Feature - US-19
 * Three-zone layout: Compact ChatView + Activity Feed + AI Digest Panel
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
  DigestCategory,
  DigestActionType,
  DigestEntityType,
  DigestSuggestion,
  DigestGeneratedBy,
  DigestResponse,
  DigestRefreshResponse,
  DismissSuggestionPayload,
  CreateNoteFromChatPayload,
  CreateNoteFromChatResponse,
  HomepageZone,
} from './types';

// API client
export { homepageApi } from './api/homepage-api';

// Stores
export { HomepageUIStore } from './stores/HomepageUIStore';

// Constants
export {
  ITEMS_PER_PAGE,
  ACTIVITY_STALE_TIME,
  DIGEST_STALE_TIME,
  MAX_ANNOTATION_PREVIEW_LENGTH,
  CHAT_MAX_HEIGHT,
  CHAT_MOBILE_BREAKPOINT,
  CHAT_ANIMATION_DURATION,
  DAY_GROUP_LABELS,
  DAY_GROUP_ORDER,
  DIGEST_CATEGORY_LABELS,
} from './constants';

// Components
export { HomepageHub } from './components/HomepageHub';
