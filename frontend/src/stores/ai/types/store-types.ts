/**
 * PilotSpaceStore local type definitions.
 *
 * Extracted from PilotSpaceStore.ts to keep files under 700-line limit.
 *
 * @module stores/ai/types/store-types
 */
import type { TaskStatus } from './events';
import type { ConfidenceTag } from './skills';

/**
 * Task state for long-running operations.
 */
export interface TaskState {
  id: string;
  subject: string;
  status: TaskStatus;
  progress: number;
  description?: string;
  currentStep?: string;
  totalSteps?: number;
  estimatedSecondsRemaining?: number;
  /** Subagent name executing this task */
  agentName?: string;
  /** AI model used by this subagent */
  model?: string;
  /** Creation timestamp */
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Approval request state per DD-003.
 */
export interface ApprovalRequest {
  requestId: string;
  actionType: string;
  description: string;
  consequences?: string;
  affectedEntities: Array<{
    type: string;
    id: string;
    name: string;
    preview?: unknown;
  }>;
  urgency: 'low' | 'medium' | 'high';
  proposedContent?: unknown;
  expiresAt: Date;
  confidenceTag?: ConfidenceTag;
  createdAt: Date;
}

export interface NoteContext {
  noteId: string;
  selectedText?: string;
  selectedBlockIds?: string[];
  noteTitle?: string;
}

export interface IssueContext {
  issueId: string;
  projectId?: string;
  issueTitle?: string;
  issueStatus?: string;
}

/**
 * Homepage context data injected when user is on the homepage.
 * Provides workspace digest summary for AI awareness.
 */
export interface HomepageContextData {
  digestSummary: string;
  totalSuggestionCount: number;
  staleIssueCount: number;
  cycleRiskCount: number;
  recentNotes: Array<{ id: string; title: string }>;
}
