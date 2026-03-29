/**
 * SSE event types for Skill Generator pipeline.
 * Defines TypeScript interfaces and type guards for skill generation events
 * streamed from the backend during conversational skill creation.
 *
 * @module stores/ai/types/events-skill-gen
 * @see backend/src/pilot_space/ai/agents/skill_generator_service.py
 */

import type { SSEEvent } from './events';

/** Partial skill content streaming during generation. */
export interface SkillDraftEvent extends SSEEvent {
  type: 'skill_draft';
  data: {
    sessionId: string;
    content: string;
    isPartial: boolean;
  };
}

/** Complete skill preview with all metadata. */
export interface SkillPreviewEvent extends SSEEvent {
  type: 'skill_preview';
  data: {
    sessionId: string;
    name: string;
    description: string;
    category: string;
    icon: string;
    skillContent: string;
    examplePrompts: string[];
    contextRequirements: string[];
    toolDeclarations: string[];
    graphData: {
      nodes: Array<{
        id: string;
        type: string;
        position: { x: number; y: number };
        data: Record<string, unknown>;
      }>;
      edges: Array<{
        id: string;
        source: string;
        target: string;
        type?: string;
      }>;
      viewport?: { x: number; y: number; zoom: number };
    } | null;
  };
}

/** Confirmation after skill save. */
export interface SkillSavedEvent extends SSEEvent {
  type: 'skill_saved';
  data: {
    skillId: string;
    skillName: string;
    saveType: 'personal' | 'workspace';
  };
}

/** Real-time graph node/edge CRUD during conversation. */
export interface GraphUpdateEvent extends SSEEvent {
  type: 'graph_update';
  data: {
    sessionId: string;
    operation: 'add_node' | 'update_node' | 'remove_node' | 'add_edge' | 'remove_edge';
    payload: Record<string, unknown>;
  };
}

// Type guard functions

export function isSkillDraftEvent(event: SSEEvent): event is SkillDraftEvent {
  return event.type === 'skill_draft';
}

export function isSkillPreviewEvent(event: SSEEvent): event is SkillPreviewEvent {
  return event.type === 'skill_preview';
}

export function isSkillSavedEvent(event: SSEEvent): event is SkillSavedEvent {
  return event.type === 'skill_saved';
}

export function isGraphUpdateEvent(event: SSEEvent): event is GraphUpdateEvent {
  return event.type === 'graph_update';
}
