/**
 * ChatView - Main conversational AI interface
 * Following pilotspace-agent-architecture.md v1.5.0
 *
 * Integrates:
 * - Message list with streaming
 * - Task panel for tracking agent progress
 * - Approval overlay for human-in-the-loop (DD-003)
 * - Chat input with skill/agent menus
 * - Context management (note, issue, project)
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { AgentTask } from './types';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList/MessageList';
import { TaskPanel } from './TaskPanel/TaskPanel';
import { ApprovalOverlay } from './ApprovalOverlay/ApprovalOverlay';
import { ChatInput } from './ChatInput/ChatInput';

interface ChatViewProps {
  store: PilotSpaceStore;
  userName?: string;
  userAvatar?: string;
  className?: string;
}

export const ChatView = observer<ChatViewProps>(({ store, userName, userAvatar, className }) => {
  const [inputValue, setInputValue] = useState('');
  const [taskPanelOpen, setTaskPanelOpen] = useState(true);

  // Convert TaskState to AgentTask for TaskPanel
  const agentTasks = useMemo((): AgentTask[] => {
    return Array.from(store.tasks.values()).map((task) => ({
      id: task.id,
      subject: task.subject,
      description: task.description || '',
      activeForm: task.currentStep || task.subject,
      // Map 'blocked' to 'pending' since AgentTask doesn't support blocked
      status: task.status === 'blocked' ? 'pending' : task.status,
      createdAt: task.createdAt,
      completedAt: task.status === 'completed' ? task.updatedAt : undefined,
    }));
  }, [store.tasks]);

  const activeAgentTasks = useMemo(
    () => agentTasks.filter((t) => t.status === 'pending' || t.status === 'in_progress'),
    [agentTasks]
  );

  const completedAgentTasks = useMemo(
    () => agentTasks.filter((t) => t.status === 'completed'),
    [agentTasks]
  );

  // Convert ApprovalRequest to ChatView ApprovalRequest
  const chatViewApprovals = useMemo(() => {
    return store.pendingApprovals.map((req) => ({
      id: req.requestId,
      agentName: '', // TODO: Extract from context when available
      actionType: req.actionType,
      status: 'pending' as const,
      contextPreview: req.description,
      payload: req.proposedContent as Record<string, unknown> | undefined,
      createdAt: req.createdAt,
      expiresAt: req.expiresAt,
      reasoning: req.consequences,
    }));
  }, [store.pendingApprovals]);

  // Auto-open task panel when tasks exist
  useEffect(() => {
    if (store.tasks.size > 0 && !taskPanelOpen) {
      setTaskPanelOpen(true);
    }
  }, [store.tasks.size, taskPanelOpen]);

  const handleSubmit = useCallback(async () => {
    if (!inputValue.trim() || store.isStreaming) return;

    try {
      await store.sendMessage(inputValue.trim());
      setInputValue('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [inputValue, store]);

  const handleClearConversation = useCallback(() => {
    if (confirm('Are you sure you want to clear this conversation?')) {
      store.clearConversation();
      setInputValue('');
    }
  }, [store]);

  const handleAbort = useCallback(() => {
    store.abort();
  }, [store]);

  const handleClearNoteContext = useCallback(() => {
    store.setNoteContext(null);
  }, [store]);

  const handleClearIssueContext = useCallback(() => {
    store.setIssueContext(null);
  }, [store]);

  const handleClearProjectContext = useCallback(() => {
    store.setProjectContext(null);
  }, [store]);

  const handleApproveAction = useCallback(
    async (id: string, modifications?: Record<string, unknown>) => {
      await store.approveAction(id, modifications);
    },
    [store]
  );

  const handleRejectAction = useCallback(
    async (id: string, reason: string) => {
      await store.rejectAction(id, reason);
    },
    [store]
  );

  return (
    <div className={cn('flex flex-col h-full bg-background', className)}>
      {/* Header */}
      <ChatHeader
        title="PilotSpace AI"
        isStreaming={store.isStreaming}
        activeTaskCount={store.activeTasks.length}
        sessionId={store.sessionId}
        onClear={handleClearConversation}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Messages */}
        <MessageList
          messages={store.messages}
          isStreaming={store.isStreaming}
          streamContent={store.streamContent}
          userName={userName}
          userAvatar={userAvatar}
          className="flex-1"
        />

        {/* Task panel */}
        {store.tasks.size > 0 && (
          <div className="px-4 pb-4">
            <TaskPanel
              tasks={agentTasks}
              activeTasks={activeAgentTasks}
              completedTasks={completedAgentTasks}
              isOpen={taskPanelOpen}
              onToggle={() => setTaskPanelOpen(!taskPanelOpen)}
            />
          </div>
        )}

        {/* Error display */}
        {store.error && (
          <div className="px-4 pb-4">
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
              <p className="text-sm text-destructive">{store.error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        isStreaming={store.isStreaming}
        isDisabled={store.hasUnresolvedApprovals}
        noteContext={
          store.noteContext
            ? {
                noteId: store.noteContext.noteId,
                selectedText: store.noteContext.selectedText,
                selectedBlockIds: store.noteContext.selectedBlockIds,
              }
            : null
        }
        issueContext={
          store.issueContext
            ? {
                issueId: store.issueContext.issueId,
                projectId: '', // TODO: Add projectId to store.issueContext
                title: store.issueContext.issueTitle || '',
                description: '',
              }
            : null
        }
        projectContext={null} // TODO: Add projectContext to store
        onClearNoteContext={handleClearNoteContext}
        onClearIssueContext={handleClearIssueContext}
        onClearProjectContext={handleClearProjectContext}
        onAbort={handleAbort}
      />

      {/* Approval overlay */}
      <ApprovalOverlay
        approvals={chatViewApprovals}
        onApprove={handleApproveAction}
        onReject={handleRejectAction}
      />
    </div>
  );
});

ChatView.displayName = 'ChatView';
