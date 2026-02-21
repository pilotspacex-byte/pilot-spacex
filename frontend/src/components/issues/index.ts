export { IssueCard } from './IssueCard';
export type { IssueCardProps } from './IssueCard';

export { IssuePrioritySelect } from './IssuePrioritySelect';
export type { IssuePrioritySelectProps, PrioritySuggestion } from './IssuePrioritySelect';

export { IssueStateSelect } from './IssueStateSelect';
export type { IssueStateSelectProps } from './IssueStateSelect';

export { IssueTypeSelect } from './IssueTypeSelect';
export type { IssueTypeSelectProps } from './IssueTypeSelect';

export { CycleSelector } from './CycleSelector';
export type { CycleSelectorProps } from './CycleSelector';

export { EstimateSelector } from './EstimateSelector';
export type { EstimateSelectorProps } from './EstimateSelector';

export { LabelSelector } from './LabelSelector';
export type { LabelSelectorProps, LabelSuggestion } from './LabelSelector';

export { AssigneeSelector } from './AssigneeSelector';
export type { AssigneeSelectorProps, AssigneeRecommendation } from './AssigneeSelector';

export { DuplicateWarning } from './DuplicateWarning';
export type { DuplicateWarningProps, DuplicateCandidate } from './DuplicateWarning';

/** @deprecated Use BoardView from @/features/issues/components/views/board instead */
export { IssueBoard } from './IssueBoard';
export type { IssueBoardProps } from './IssueBoard';

export { IssueModal } from './IssueModal';
export type { IssueModalProps } from './IssueModal';

export {
  ContextItemList,
  type ContextItemListProps,
  type RelatedItem,
  type RelatedItemType,
} from './ContextItemList';

export {
  TaskChecklist,
  type TaskChecklistProps,
  type TaskItem,
  type EffortSize,
} from './TaskChecklist';

export { ClaudeCodePrompt, type ClaudeCodePromptProps } from './ClaudeCodePrompt';
