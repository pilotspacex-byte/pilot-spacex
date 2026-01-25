/**
 * Integration components index.
 *
 * Phase 6 (US-18 GitHub Integration) components.
 * Phase 7 (US-3 PR Review) components.
 */

export { GitHubIntegration, type GitHubIntegrationProps } from './GitHubIntegration';

export { BranchSuggestion, useBranchName, type BranchSuggestionProps } from './BranchSuggestion';

export {
  PRLinkBadge,
  PRLinkCard,
  PRLinkBadgeFromData,
  PRLinkBadgeList,
  type PRLinkBadgeProps,
  type PRLinkBadgeListProps,
  type PRState,
} from './PRLinkBadge';

export { CommitList, type CommitListProps } from './CommitList';

// Phase 7: PR Review (US-3)
export {
  PRReviewStatus,
  type PRReviewStatusProps,
  type ReviewResult,
  type ReviewStatus,
} from './PRReviewStatus';

export {
  ReviewCommentCard,
  type ReviewCommentCardProps,
  type ReviewComment,
  type ReviewSeverity,
  type ReviewCategory,
} from './ReviewCommentCard';

export {
  ReviewSummary,
  type ReviewSummaryProps,
  type ApprovalRecommendation,
} from './ReviewSummary';
