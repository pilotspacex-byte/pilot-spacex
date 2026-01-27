/**
 * Types for PilotSpace AI ChatView components
 * Following pilotspace-agent-architecture.md v1.5.0
 */

/**
 * Chat message in a conversation
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  toolCalls?: ToolCall[];
  timestamp: Date;
}

/**
 * Tool call executed by the agent
 */
export interface ToolCall {
  id: string;
  name: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  input: Record<string, unknown>;
  output?: unknown;
  error?: string;
}

/**
 * Agent task tracked in the UI
 */
export interface AgentTask {
  id: string;
  subject: string;
  description: string;
  activeForm: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  skill?: string;
  subagent?: string;
  createdAt?: Date;
  completedAt?: Date;
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
 * SSE event types from backend
 */
export type SSEEventType =
  | 'message_start'
  | 'content_block_start'
  | 'text_delta'
  | 'tool_use'
  | 'approval_request'
  | 'task_progress'
  | 'task_complete'
  | 'message_stop'
  | 'error';

/**
 * SSE event from backend
 */
export interface SSEEvent {
  type: SSEEventType;
  data?: unknown;
}

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
