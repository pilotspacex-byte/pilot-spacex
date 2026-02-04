/**
 * Types for PilotSpace AI ChatView components
 * Following pilotspace-agent-architecture.md v1.5.0
 */

import type {
  ChatMessage as _ChatMessage,
  ToolCall as _ToolCall,
} from '@/stores/ai/types/conversation';

/**
 * Chat message and tool call types — re-exported from canonical store types.
 * Use stores/ai/types/conversation.ts for all conversation data.
 */
export type ChatMessage = _ChatMessage;
export type ToolCall = _ToolCall;

/**
 * Agent task tracked in the UI (T071-T074: Added progress tracking)
 */
export interface AgentTask {
  id: string;
  subject: string;
  description: string;
  activeForm: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  skill?: string;
  subagent?: string;
  /** AI model used by this subagent (e.g., "Claude Opus", "Claude Sonnet") */
  model?: string;
  createdAt?: Date;
  completedAt?: Date;
  // Progress tracking (T071-T074)
  progress?: number;
  currentStep?: string;
  totalSteps?: number;
  estimatedSecondsRemaining?: number;
}

/**
 * Approval request for critical actions (DD-003)
 */
export interface ApprovalRequest {
  id: string;
  agentName: string;
  actionType: string;
  status: 'pending' | 'approved' | 'rejected';
  contextPreview: string;
  payload?: Record<string, unknown>;
  createdAt: Date;
  expiresAt: Date;
  reasoning?: string;
}

/**
 * Note context for conversation
 */
export interface NoteContext {
  noteId: string;
  noteTitle?: string;
  selectedText?: string;
  selectedBlockIds?: string[];
  cursorPosition?: number;
}

/**
 * Issue context for conversation
 */
export interface IssueContext {
  issueId: string;
  projectId: string;
  title: string;
  description?: string;
}

/**
 * Project context for conversation
 */
export interface ProjectContext {
  projectId: string;
  name: string;
  slug: string;
}

/**
 * Skill definition for menu
 */
export interface SkillDefinition {
  name: string;
  description: string;
  category: 'writing' | 'notes' | 'issues' | 'code' | 'documentation' | 'planning';
  icon: string;
  examples?: string[];
}

/**
 * Agent definition for menu
 */
export interface AgentDefinition {
  name: string;
  description: string;
  icon: string;
  capabilities: string[];
}

/**
 * SSE event types — re-exported from canonical store types.
 * Use stores/ai/types/events.ts for all SSE event handling.
 */
export type { SSEEventType, SSEEvent } from '@/stores/ai/types/events';

/**
 * PilotSpaceStore interface (from architecture)
 */
export interface IPilotSpaceStore {
  // Conversation
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  sessionId: string | null;
  error: string | null;

  // Tasks
  tasks: Map<string, AgentTask>;
  readonly activeTasks: AgentTask[];
  readonly completedTasks: AgentTask[];

  // Approvals
  pendingApprovals: ApprovalRequest[];
  readonly hasUnresolvedApprovals: boolean;

  // Context
  noteContext: NoteContext | null;
  issueContext: IssueContext | null;
  projectContext: ProjectContext | null;
  activeSkill: string | null;
  skillArgs: string | null;
  mentionedAgents: string[];

  // Actions
  sendMessage(content: string): Promise<void>;
  setNoteContext(ctx: NoteContext | null): void;
  setIssueContext(ctx: IssueContext | null): void;
  setProjectContext(ctx: ProjectContext | null): void;
  setActiveSkill(skill: string, args?: string): void;
  addMentionedAgent(agent: string): void;
  approveAction(id: string, modifications?: Record<string, unknown>): Promise<void>;
  rejectAction(id: string, reason: string): Promise<void>;
  abort(): void;
  clearConversation(): void;
}
