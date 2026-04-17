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
  HomepageActivityData,
  HomepageActivityResponse,
  BranchStatusBrief,
  PRStatusBrief,
  DevObjectStatus,
  StaleIssueInfo,
  SuggestionCardData,
} from './types';

// API client
export { homepageApi } from './api/homepage-api';

// Constants
export {
  ITEMS_PER_PAGE,
  ACTIVITY_STALE_TIME,
  STALE_THRESHOLD_DAYS,
  SPARKLINE_POINT_COUNT,
  DEV_OBJECT_STALE_TIME,
} from './constants';

// Components
export { HomepageHub } from './components/HomepageHub';
export { HomepageV3 } from './components/HomepageV3';
export { RedFlagRow } from './components/RedFlagRow';
export { ContinueCard } from './components/ContinueCard';
export { WorkspacePill } from './components/WorkspacePill';
export { ChatHeroInput } from './components/ChatHeroInput';
export { QuickActionCarousel } from './components/QuickActionCarousel';
export { ExamplePrompts } from './components/ExamplePrompts';
export { RecentWorkSection } from './components/RecentWorkSection';
export { ActiveRoutines } from './components/ActiveRoutines';
export { SprintProgress } from './components/SprintProgress';
export { RecentConversations } from './components/RecentConversations';
export {
  SectionDivider,
  NoteEntry,
  IssueEntry,
  ProjectEntry,
  NoteSkeleton,
  IssueSkeleton,
  OnboardingBanner,
  STATE_COLORS,
} from './components/BriefEntries';
export { IssueDetailSheet } from './components/IssueDetailSheet';
export { NoteContextBadge } from './components/NoteContextBadge';
export { DevObjectIndicators } from './components/DevObjectIndicators';
export { SprintSparkline } from './components/SprintSparkline';
export { StaleLogicAlert } from './components/StaleLogicAlert';
export { SDLCSuggestionCards } from './components/SDLCSuggestionCards';

// Hooks
export { useIssueDevObjects } from './hooks/useIssueDevObjects';
export { useActiveCycleMetrics } from './hooks/useActiveCycleMetrics';
export { useStaleIssueDetection, detectStaleIssues } from './hooks/useStaleIssueDetection';
