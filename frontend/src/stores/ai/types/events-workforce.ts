/**
 * Feature 015: AI Workforce Platform — intent and skill lifecycle SSE event types.
 *
 * These events are emitted by the backend's agent loop during intent detection,
 * confirmation, execution, and skill completion phases.
 *
 * @module stores/ai/types/events-workforce
 * @see backend/src/pilot_space/ai/agents/pilotspace_agent.py
 */

import type { SSEEvent } from './events';

// ── Intent lifecycle events ───────────────────────────────────────────────────

/** Emitted when the agent detects an actionable intent in the user's message. */
export interface IntentDetectedEvent extends SSEEvent {
  type: 'intent_detected';
  data: {
    intentId: string;
    what: string;
    why: string;
    constraints: string[];
    confidence: number;
  };
}

/** Emitted when the user confirms a detected intent for execution. */
export interface IntentConfirmedEvent extends SSEEvent {
  type: 'intent_confirmed';
  data: { intentId: string };
}

/** Emitted when the agent begins executing a confirmed intent via a skill. */
export interface IntentExecutingEvent extends SSEEvent {
  type: 'intent_executing';
  data: {
    intentId: string;
    skillName: string;
    intentSummary: string;
    totalSteps: number;
  };
}

/** Emitted when intent execution finishes (success or failure). */
export interface IntentCompletedEvent extends SSEEvent {
  type: 'intent_completed';
  data: {
    intentId: string;
    success: boolean;
    summary: string;
    artifacts: Record<string, unknown>[];
    errorMessage?: string;
    partialOutput?: boolean;
  };
}

/** Emitted when a skill completes and may require approval for its artifacts. */
export interface SkillCompletedEvent extends SSEEvent {
  type: 'skill_completed';
  data: {
    intentId: string;
    artifacts: Record<string, unknown>[];
    requiresApproval: boolean;
    approvalId?: string;
  };
}

/** Emitted to report current agent concurrency queue state. */
export interface QueueUpdateEvent extends SSEEvent {
  type: 'queue_update';
  data: {
    runningCount: number;
    queuedCount: number;
    maxConcurrent: number;
  };
}
