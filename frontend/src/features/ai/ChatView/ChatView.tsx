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
 * - Session persistence (T075-T079)
 */

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Square } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import type { AgentTask } from './types';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList/MessageList';
import { TaskPanel } from './TaskPanel/TaskPanel';
import { ApprovalOverlay } from './ApprovalOverlay/ApprovalOverlay';
import { ChatInput } from './ChatInput/ChatInput';
import { SuggestionCard } from './MessageList/SuggestionCard';
import { QuestionCard } from './MessageList/QuestionCard';
import { ChatViewErrorBoundary } from './ChatViewErrorBoundary';

/**
 * Destructive actions that require modal overlay approval (DD-003).
 * Non-destructive actions render as inline SuggestionCard instead.
 */
const DESTRUCTIVE_ACTIONS = new Set([
  'delete_issue',
  'merge_pr',
  'archive_workspace',
  'delete_note',
  'delete_comment',
]);

export function isDestructiveAction(actionType: string): boolean {
  return DESTRUCTIVE_ACTIONS.has(actionType);
}

interface ChatViewProps {
  store: PilotSpaceStore;
  userName?: string;
  userAvatar?: string;
  /** Auto-focus the chat input when the view becomes visible */
  autoFocus?: boolean;
  /** Callback to close the chat panel */
  onClose?: () => void;
  className?: string;
}

const ChatViewInternal = observer<ChatViewProps>(
  ({ store, userName, userAvatar, autoFocus, onClose, className }) => {
    const [inputValue, setInputValue] = useState('');
    const [taskPanelOpen, setTaskPanelOpen] = useState(true);
    const [showClearDialog, setShowClearDialog] = useState(false);
    const prefersReducedMotion = useReducedMotion();

    // Initialize SessionListStore (T075-T079)
    const [sessionListStore] = useState(
      () => new SessionListStore(store as unknown as import('@/stores/ai/AIStore').AIStore)
    );

    // Fetch sessions on mount
    useEffect(() => {
      sessionListStore.fetchSessions();
    }, [sessionListStore]);

    // Load conversation history for note context when ChatView opens
    const loadedContextRef = useRef<string | null>(null);
    useEffect(() => {
      const noteId = store.noteContext?.noteId;
      if (!noteId || store.messages.length > 0 || loadedContextRef.current === noteId) return;

      loadedContextRef.current = noteId;
      sessionListStore.resumeSessionForContext(noteId, 'note');
    }, [store.noteContext?.noteId, store.messages.length, sessionListStore]);

    // Convert TaskState to AgentTask for TaskPanel with progress data
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
        // Include progress data for T071-T074
        progress: task.progress,
        currentStep: task.currentStep,
        totalSteps: task.totalSteps,
        estimatedSecondsRemaining: task.estimatedSecondsRemaining,
        // Subagent identity
        subagent: task.agentName,
        model: task.model,
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

    // Split approvals: non-destructive inline cards vs destructive modal overlay
    const { inlineApprovals, modalApprovals } = useMemo(() => {
      const inline: typeof chatViewApprovals = [];
      const modal: typeof chatViewApprovals = [];

      for (const req of chatViewApprovals) {
        if (isDestructiveAction(req.actionType)) {
          modal.push(req);
        } else {
          inline.push(req);
        }
      }

      return { inlineApprovals: inline, modalApprovals: modal };
    }, [chatViewApprovals]);

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
      } catch (error) {
        store.error = error instanceof Error ? error.message : 'Failed to send message';
      }
    }, [inputValue, store]);

    const handleClearConversation = useCallback(() => {
      setShowClearDialog(true);
    }, []);

    const handleConfirmClear = useCallback(() => {
      store.clearConversation();
      setInputValue('');
      setShowClearDialog(false);
    }, [store]);

    const handleAbort = useCallback(() => {
      store.abort();
    }, [store]);

    const handleQuestionSubmit = useCallback(
      async (questionId: string, answer: string) => {
        try {
          await store.submitQuestionAnswer(questionId, answer);
        } catch (error) {
          store.error = error instanceof Error ? error.message : 'Failed to submit answer';
        }
      },
      [store]
    );

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

    const handleNewSession = useCallback(() => {
      store.clear();
      setInputValue('');
    }, [store]);

    const handleSelectSession = useCallback(
      async (sessionId: string) => {
        await sessionListStore.resumeSession(sessionId);
      },
      [sessionListStore]
    );

    // Prepare recent sessions for dropdown
    const recentSessions = useMemo(
      () =>
        sessionListStore.activeSessions.slice(0, 5).map((s) => ({
          sessionId: s.sessionId,
          title: s.title,
          updatedAt: s.updatedAt,
        })),
      [sessionListStore.activeSessions]
    );

    return (
      <div className={cn('flex flex-col h-full bg-background', className)} data-testid="chat-view">
        {/* Header with session selector (T075-T079) */}
        <ChatHeader
          title="PilotSpace Agent"
          isStreaming={store.isStreaming}
          activeTaskCount={store.activeTasks.length}
          sessionId={store.sessionId}
          recentSessions={recentSessions}
          onClear={handleClearConversation}
          onClose={onClose}
          onNewSession={handleNewSession}
          onSelectSession={handleSelectSession}
        />

        {/* Main content area - relative for floating abort button */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Messages */}
          <MessageList
            messages={store.messages}
            isStreaming={store.isStreaming}
            streamContent={store.streamContent}
            thinkingContent={store.streamingState.thinkingContent}
            isThinking={store.streamingState.isThinking}
            userName={userName}
            userAvatar={userAvatar}
            className="flex-1"
          />

          {/* Inline question card for AskUserQuestion events */}
          {store.pendingQuestion && (
            <div className="px-4 pb-3">
              <QuestionCard
                questionId={store.pendingQuestion.questionId}
                questions={store.pendingQuestion.questions}
                onSubmit={handleQuestionSubmit}
                isResolved={!!store.pendingQuestion.resolvedAnswer}
                resolvedAnswer={store.pendingQuestion.resolvedAnswer}
              />
            </div>
          )}

          {/* Floating abort button - overlays bottom of message area */}
          <AnimatePresence>
            {store.isStreaming && (
              <motion.div
                initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.15 }}
                className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10"
              >
                <Button
                  data-testid="abort-button"
                  variant="secondary"
                  size="sm"
                  onClick={handleAbort}
                  className={cn(
                    'gap-1.5 rounded-full shadow-lg',
                    'border border-border/60 bg-background/90 backdrop-blur-sm',
                    'hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30',
                    'transition-colors'
                  )}
                >
                  <Square className="h-3 w-3 fill-current" />
                  <span className="text-xs font-medium">Stop</span>
                </Button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Task panel */}
          {store.tasks.size > 0 && (
            <div className="px-4 pb-3">
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
            <div className="px-3 pb-3">
              <div
                className="rounded-lg border border-destructive/50 bg-destructive/10 p-2.5"
                data-testid="error-message"
              >
                <p className="text-xs text-destructive">{store.error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Inline suggestion cards for non-destructive approvals */}
        {inlineApprovals.map((approval) => (
          <SuggestionCard
            key={approval.id}
            approval={approval}
            onApprove={handleApproveAction}
            onReject={handleRejectAction}
          />
        ))}

        {/* Input */}
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          autoFocus={autoFocus}
          isStreaming={store.isStreaming}
          isDisabled={store.hasUnresolvedApprovals}
          noteContext={
            store.noteContext
              ? {
                  noteId: store.noteContext.noteId,
                  noteTitle: store.noteContext.noteTitle,
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
        />

        {/* Modal overlay only for destructive actions (DD-003) */}
        <ApprovalOverlay
          approvals={modalApprovals}
          onApprove={handleApproveAction}
          onReject={handleRejectAction}
        />

        {/* Clear conversation confirmation dialog */}
        <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear Conversation?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove all messages from this conversation. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleConfirmClear}>Clear</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    );
  }
);

ChatViewInternal.displayName = 'ChatViewInternal';

// Wrap with error boundary
export const ChatView = observer<ChatViewProps>((props) => {
  const handleRetry = useCallback(() => {
    // Clear store error state on retry
    if (props.store.error) {
      props.store.clear();
    }
  }, [props.store]);

  return (
    <ChatViewErrorBoundary onRetry={handleRetry}>
      <ChatViewInternal {...props} />
    </ChatViewErrorBoundary>
  );
});

ChatView.displayName = 'ChatView';
