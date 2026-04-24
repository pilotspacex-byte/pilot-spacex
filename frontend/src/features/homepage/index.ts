/**
 * Homepage feature barrel — Phase 88 Plan 04 cutover.
 *
 * Pre-Phase 88: this barrel exposed the v2 dashboard (HomepageHub +
 * DailyBrief children, suggestion cards, dev-object indicators, etc.).
 *
 * Post-Phase 88: the workspace home renders the chat-first <Launchpad />.
 * The v2 dashboard files are deleted in Plan 04 Task 6 (refactor commit
 * tagged MIG-01). The hooks `useIssueDevObjects`, `useActiveCycleMetrics`,
 * and `useStaleIssueDetection` remain on disk (no longer barrel-exported)
 * pending a Phase 89+ cleanup; their backend endpoints (`/homepage/digest`,
 * `/homepage/activity`) are NOT removed this phase.
 */

// Types — kept for downstream features that may consume the digest /
// activity payloads via direct imports (none in tree at cutover time, but
// the types are still authored here).
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
} from './types';

// API client — still used by useHomepageActivity / useWorkspaceDigest /
// useRedFlags via direct hook imports.
export { homepageApi } from './api/homepage-api';

// Constants — still consumed by the surviving hooks.
export {
  ITEMS_PER_PAGE,
  ACTIVITY_STALE_TIME,
  STALE_THRESHOLD_DAYS,
  SPARKLINE_POINT_COUNT,
  DEV_OBJECT_STALE_TIME,
} from './constants';

// Components — Launchpad assembly + its child building blocks.
export { Launchpad } from './Launchpad';
export { HomepageGreeting } from './components/HomepageGreeting';
export { HomeComposer } from './components/HomeComposer';
export { RedFlagStrip } from './components/RedFlagStrip';
export { SuggestedPromptsRow } from './components/SuggestedPromptsRow';
export { ContinueCard } from './components/ContinueCard';

// Hooks — public surface for the launchpad children.
export { useRedFlags } from './hooks/use-red-flags';
export { useLastChatSession } from './hooks/use-last-chat-session';
