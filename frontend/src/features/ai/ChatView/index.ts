/**
 * ChatView - Unified conversational AI interface
 * Phase 4.2: ChatView Component Tree (pilotspace-agent-architecture-remediation-plan.md)
 */

export { ChatView } from './ChatView';
export { ChatViewErrorBoundary } from './ChatViewErrorBoundary';
export { ChatHeader } from './ChatHeader';

// MessageList components
export { MessageList } from './MessageList/MessageList';
export { MessageGroup } from './MessageList/MessageGroup';
export { UserMessage } from './MessageList/UserMessage';
export { AssistantMessage } from './MessageList/AssistantMessage';
export { ToolCallList } from './MessageList/ToolCallList';
export { StreamingContent } from './MessageList/StreamingContent';

// TaskPanel components
export { TaskPanel } from './TaskPanel/TaskPanel';
export { TaskList } from './TaskPanel/TaskList';
export { TaskItem } from './TaskPanel/TaskItem';
export { TaskSummary } from './TaskPanel/TaskSummary';

// ApprovalOverlay components
export { ApprovalOverlay } from './ApprovalOverlay/ApprovalOverlay';
export { ApprovalDialog } from './ApprovalOverlay/ApprovalDialog';
export { IssuePreview } from './ApprovalOverlay/IssuePreview';
export { ContentDiff } from './ApprovalOverlay/ContentDiff';
export { GenericJSON } from './ApprovalOverlay/GenericJSON';

// ChatInput components
export { ChatInput } from './ChatInput/ChatInput';
export { ContextIndicator } from './ChatInput/ContextIndicator';
export { SkillMenu } from './ChatInput/SkillMenu';
export { AgentMenu } from './ChatInput/AgentMenu';

// Types and constants
export * from './types';
export { SKILLS, AGENTS, SKILL_CATEGORIES } from './constants';
