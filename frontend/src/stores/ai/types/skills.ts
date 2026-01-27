/**
 * Skill types for PilotSpaceStore.
 * Defines skill metadata, invocation state, and results.
 *
 * Skills are user-facing capabilities triggered via slash commands (e.g., "/extract-issues").
 * They map to backend agents but provide a simplified, task-oriented interface.
 *
 * @module stores/ai/types/skills
 */

import type { ConversationContext } from './conversation';

/**
 * Skill definition metadata.
 * Used for discovery, UI display, and command palette.
 */
export interface SkillDefinition {
  /** Skill identifier (e.g., "extract-issues") */
  name: string;
  /** Human-readable description */
  description: string;
  /** Skill category for grouping in UI */
  category: SkillCategory;
  /** Icon identifier for UI display (Lucide icon name) */
  icon?: string;
  /** Keyboard shortcut (e.g., "Cmd+Shift+E") */
  shortcut?: string;
  /** Whether skill requires context (note/issue/project) */
  requiresContext?: boolean;
  /** Supported context types */
  contextTypes?: Array<'note' | 'issue' | 'project' | 'workspace'>;
  /** Example usage for command palette */
  example?: string;
}

/**
 * Skill category for UI grouping.
 * - issue-management: Creating, updating, linking issues
 * - writing: Ghost text, margin annotations, content generation
 * - analysis: Code review, task decomposition, duplicate detection
 * - documentation: Doc generation, diagram creation
 */
export type SkillCategory = 'issue-management' | 'writing' | 'analysis' | 'documentation';

/**
 * Active skill invocation.
 * Tracks an in-progress skill execution.
 */
export interface SkillInvocation {
  /** Invocation ID (UUIDv4) */
  id: string;
  /** Skill being invoked */
  skillName: string;
  /** Skill arguments (parsed from slash command) */
  args?: Record<string, unknown>;
  /** Context at invocation time */
  context: ConversationContext;
  /** Invocation start timestamp */
  startedAt: Date;
  /** Current invocation status */
  status: SkillInvocationStatus;
  /** Associated message ID */
  messageId?: string;
}

/**
 * Skill invocation status.
 * - pending: Queued for execution
 * - running: Currently executing
 * - awaiting_approval: Requires human approval (per DD-003)
 * - completed: Successfully finished
 * - failed: Execution failed
 * - cancelled: User cancelled
 */
export type SkillInvocationStatus =
  | 'pending'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'failed'
  | 'cancelled';

/**
 * Skill execution result.
 * Returned after skill completes.
 */
export interface SkillResult {
  /** Invocation ID this result belongs to */
  invocationId: string;
  /** Skill name */
  skillName: string;
  /** Execution status */
  status: 'success' | 'error' | 'partial';
  /** Result payload (skill-specific structure) */
  output: unknown;
  /** AI confidence tag per DD-048 */
  confidenceTag?: ConfidenceTag;
  /** Execution duration in milliseconds */
  duration: number;
  /** Error details if status is 'error' */
  error?: SkillError;
  /** Cost incurred for this execution (USD) */
  costUsd?: number;
}

/**
 * Skill execution error details.
 */
export interface SkillError {
  /** Error code (e.g., "RATE_LIMITED", "CONTEXT_EXCEEDED") */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Whether error is retryable */
  retryable: boolean;
  /** Suggested retry delay in milliseconds */
  retryAfter?: number;
}

/**
 * AI confidence tags per DD-048.
 *
 * Used to communicate AI certainty and guide user decision-making:
 * - RECOMMENDED: AI's top suggestion (highest confidence)
 * - DEFAULT: Standard/safe option (moderate confidence)
 * - CURRENT: Preserves existing state (no change)
 * - ALTERNATIVE: Other valid options (explored but not preferred)
 */
export type ConfidenceTag = 'RECOMMENDED' | 'DEFAULT' | 'CURRENT' | 'ALTERNATIVE';

/**
 * Available skills registry.
 * Populated from backend `/api/v1/ai/skills` endpoint.
 */
export interface SkillsRegistry {
  /** Map of skill name to definition */
  skills: Map<string, SkillDefinition>;
  /** Last registry update timestamp */
  lastUpdated: Date | null;
  /** Whether registry is currently loading */
  isLoading: boolean;
}
