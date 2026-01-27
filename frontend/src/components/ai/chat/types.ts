/**
 * Type definitions for AI Chat components
 *
 * @module components/ai/chat/types
 */

/* -----------------------------------------------------------------------------
 * Message Types
 * -------------------------------------------------------------------------- */

/**
 * Chat message role
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Tool call status
 */
export type ToolCallStatus = 'pending' | 'running' | 'complete' | 'error';

/**
 * Tool call representation
 */
export interface ToolCall {
  /** Unique identifier */
  id: string;
  /** Tool name (e.g., "read_file", "run_command") */
  name: string;
  /** Tool input parameters */
  input: Record<string, unknown>;
  /** Tool output result */
  output?: string;
  /** Execution status */
  status: ToolCallStatus;
  /** Error message if status is 'error' */
  error?: string;
  /** Execution duration in milliseconds */
  duration?: number;
}

/**
 * Thinking/reasoning block
 */
export interface ThinkingBlock {
  /** Unique identifier */
  id: string;
  /** Thinking content */
  content: string;
  /** Thinking duration in milliseconds */
  duration?: number;
  /** Whether block is collapsed */
  isCollapsed?: boolean;
}

/**
 * Chat message
 */
export interface ChatMessage {
  /** Unique identifier */
  id: string;
  /** Message role */
  role: MessageRole;
  /** Message content */
  content: string;
  /** Tool calls associated with message */
  toolCalls?: ToolCall[];
  /** Thinking blocks */
  thinking?: ThinkingBlock[];
  /** Whether message is streaming */
  isStreaming?: boolean;
  /** Message timestamp */
  timestamp: Date;
  /** User metadata */
  user?: {
    name?: string;
    avatarUrl?: string;
  };
}

/* -----------------------------------------------------------------------------
 * Context Types
 * -------------------------------------------------------------------------- */

/**
 * Note context for chat
 */
export interface NoteContext {
  /** Note ID */
  id: string;
  /** Note title */
  title: string;
  /** Selected text range (if any) */
  selection?: {
    from: number;
    to: number;
    text: string;
  };
}

/**
 * Issue context for chat
 */
export interface IssueContext {
  /** Issue ID */
  id: string;
  /** Issue identifier (e.g., "PS-123") */
  identifier: string;
  /** Issue title */
  title: string;
}

/**
 * Chat context (note or issue)
 */
export type ChatContext = NoteContext | IssueContext;

/* -----------------------------------------------------------------------------
 * Task Types
 * -------------------------------------------------------------------------- */

/**
 * Agent task status
 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * Agent task
 */
export interface AgentTask {
  /** Unique identifier */
  id: string;
  /** Task title */
  title: string;
  /** Task description */
  description?: string;
  /** Task status */
  status: TaskStatus;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Start time */
  startedAt?: Date;
  /** Completion time */
  completedAt?: Date;
  /** Error message if failed */
  error?: string;
}

/* -----------------------------------------------------------------------------
 * Approval Types
 * -------------------------------------------------------------------------- */

/**
 * Approval action type
 */
export type ApprovalActionType =
  | 'create_issue'
  | 'update_issue'
  | 'delete_issue'
  | 'run_command'
  | 'write_file';

/**
 * Approval request
 */
export interface ApprovalRequest {
  /** Unique identifier */
  id: string;
  /** Action type requiring approval */
  actionType: ApprovalActionType;
  /** Action title */
  title: string;
  /** Action description */
  description: string;
  /** Action payload */
  payload: Record<string, unknown>;
  /** Approval deadline */
  expiresAt?: Date;
  /** Callback when approved */
  onApprove: (payload: Record<string, unknown>) => Promise<void>;
  /** Callback when rejected */
  onReject: () => void;
}

/* -----------------------------------------------------------------------------
 * Skill & Agent Types
 * -------------------------------------------------------------------------- */

/**
 * Skill definition for SkillMenu
 */
export interface SkillDefinition {
  /** Skill name (slash command) */
  name: string;
  /** Human-readable description */
  description: string;
  /** Lucide icon name */
  icon: string;
  /** Whether skill requires context (note/issue) */
  requiresContext?: boolean;
  /** Skill category */
  category?: 'note' | 'issue' | 'general';
}

/**
 * Agent definition for AgentMenu
 */
export interface AgentDefinition {
  /** Agent name */
  name: string;
  /** Human-readable description */
  description: string;
  /** Lucide icon name */
  icon: string;
  /** Agent expertise areas */
  expertise?: string[];
}

/* -----------------------------------------------------------------------------
 * Chat State Types
 * -------------------------------------------------------------------------- */

/**
 * Chat state for the view
 */
export interface ChatState {
  /** All messages in conversation */
  messages: ChatMessage[];
  /** Active tasks */
  tasks: Map<string, AgentTask>;
  /** Pending approval requests */
  pendingApprovals: ApprovalRequest[];
  /** Whether AI is streaming */
  isStreaming: boolean;
  /** Current context (note or issue) */
  context?: ChatContext;
  /** Input value */
  input: string;
}

/* -----------------------------------------------------------------------------
 * Component Props Types
 * -------------------------------------------------------------------------- */

/**
 * Props for menu trigger detection
 */
export interface MenuTriggerState {
  /** Whether menu is triggered */
  isTriggered: boolean;
  /** Trigger character ('/' or '@') */
  trigger?: '/' | '@';
  /** Search query after trigger */
  query: string;
  /** Cursor position */
  cursorPosition: number;
}
