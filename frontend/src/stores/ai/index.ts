/**
 * AI Stores - Centralized exports for AI-related MobX stores.
 */

// AI Store (root)
export { AIStore, aiStore, getAIStore } from './AIStore';

// Feature Stores
export { GhostTextStore } from './GhostTextStore';
export { AIContextStore } from './AIContextStore';
export { ApprovalStore } from './ApprovalStore';
export { AISettingsStore } from './AISettingsStore';
export { PRReviewStore } from './PRReviewStore';
export { IssueExtractionStore } from './IssueExtractionStore';
export { MarginAnnotationStore } from './MarginAnnotationStore';
export { CostStore } from './CostStore';
export { PilotSpaceStore } from './PilotSpaceStore';

// Types
export type { AIContextPhase, AIContextResult } from './AIContextStore';
export type { ApprovalRequest } from '@/services/api';
export type {
  ReviewAspect,
  ReviewAspectName,
  AspectStatus,
  ReviewFinding,
  FindingSeverity,
  PRReviewResult,
  TokenUsage,
} from './PRReviewStore';
export type { ExtractedIssue } from './IssueExtractionStore';
export type { NoteAnnotation } from './MarginAnnotationStore';
export type { DateRange, CostByAgentData, CostTrendData } from './CostStore';
export type {
  TaskState,
  ApprovalRequest as PilotSpaceApprovalRequest,
  NoteContext,
  IssueContext,
} from './PilotSpaceStore';

// Conversational Agent Types
export * from './types';
