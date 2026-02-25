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
import type React from 'react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
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
import { Square, AlertCircle, X } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import type { AgentTask } from './types';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList/MessageList';
import { TaskPanel } from './TaskPanel/TaskPanel';
import { DestructiveApprovalModal } from './ApprovalOverlay/DestructiveApprovalModal';
import { ChatInput } from './ChatInput/ChatInput';
import { InlineApprovalCard } from './MessageList/InlineApprovalCard';
import { WaitingIndicator } from './WaitingIndicator';
import { ChatViewErrorBoundary } from './ChatViewErrorBoundary';
import { IntentMessageRenderer } from './MessageList/IntentMessageRenderer';
import { ConfirmAllButton } from './ConfirmAllButton';
import { QueueDepthIndicator } from './QueueDepthIndicator';
import { useIntentRehydration } from './hooks/useIntentRehydration';

/**
 * Destructive actions that require modal overlay approval (DD-003).
 * Non-destructive actions render as inline InlineApprovalCard instead.
 */
const DESTRUCTIVE_ACTIONS = new Set([
  'delete_issue',
  'merge_pr',
  'close_issue',
  'archive_workspace',
  'delete_note',
  'delete_comment',
  'unlink_issue_from_note',
  'unlink_issues',
]);

export function isDestructiveAction(actionType: string): boolean {
  return DESTRUCTIVE_ACTIONS.has(actionType);
}

/**
 * Loading skeleton for conversation resume with staggered animation
 */
function ConversationLoadingSkeleton() {
  const messageSkeletons = [
    // User message
    {
      align: 'end',
      items: [
        { h: 4, w: 48 },
        { h: 12, w: 64 },
      ],
    },
    // Assistant message
    {
      align: 'start',
      items: [
        { h: 4, w: 32 },
        { h: 20, w: 80 },
        { h: 16, w: 72 },
      ],
    },
    // User message
    {
      align: 'end',
      items: [
        { h: 4, w: 40 },
        { h: 10, w: 56 },
      ],
    },
    // Assistant message
    {
      align: 'start',
      items: [
        { h: 4, w: 36 },
        { h: 24, w: 96 },
      ],
    },
  ];

  return (
    <motion.div
      role="status"
      aria-label="Loading conversation"
      className="flex-1 overflow-y-auto px-4 py-6 space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {messageSkeletons.map((msg, idx) => (
        <motion.div
          key={idx}
          className={cn('flex', msg.align === 'end' ? 'justify-end' : 'justify-start')}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.1, duration: 0.3 }}
        >
          <div className="max-w-[80%] space-y-2">
            {msg.items.map((item, itemIdx) => (
              <Skeleton
                key={itemIdx}
                className={cn(
                  `h-${item.h} w-${item.w} rounded-xl`,
                  msg.align === 'end' && itemIdx === 0 && 'ml-auto'
                )}
                style={{ height: item.h * 4, width: item.w * 4 }}
              />
            ))}
          </div>
        </motion.div>
      ))}

      {/* Loading indicator at bottom */}
      <motion.div
        className="flex justify-center pt-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <motion.div
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, repeatDelay: 0.2 }}
          />
          <motion.div
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, repeatDelay: 0.2, delay: 0.2 }}
          />
          <motion.div
            className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, repeatDelay: 0.2, delay: 0.4 }}
          />
          <span className="ml-1">Loading conversation</span>
        </div>
      </motion.div>
    </motion.div>
  );
}

interface ChatViewProps {
  store: PilotSpaceStore;
  userName?: string;
  userAvatar?: string;
  /** Auto-focus the chat input when the view becomes visible */
  autoFocus?: boolean;
  /** Callback to close the chat panel */
  onClose?: () => void;
  /** Custom suggested prompts shown in the empty state */
  suggestedPrompts?: readonly string[];
  /** Custom empty state slot passed through to MessageList */
  emptyStateSlot?: React.ReactNode;
  /** Prompt to auto-send when ChatView mounts with an empty conversation */
  initialPrompt?: string;
  className?: string;
}

const ChatViewInternal = observer<ChatViewProps>(
  ({
    store,
    userName,
    userAvatar,
    autoFocus,
    onClose,
    suggestedPrompts,
    emptyStateSlot,
    initialPrompt,
    className,
  }) => {
    const [inputValue, setInputValue] = useState('');
    const [taskPanelOpen, setTaskPanelOpen] = useState(true);
    const [showClearDialog, setShowClearDialog] = useState(false);
    const [isResumingSession, setIsResumingSession] = useState(false);
    const [destructiveModalOpen, setDestructiveModalOpen] = useState(false);
    // Trigger to scroll MessageList to bottom after session resume
    const [scrollToBottomTrigger, setScrollToBottomTrigger] = useState(0);
    const prefersReducedMotion = useReducedMotion();

    // Initialize SessionListStore (T075-T079)
    const [sessionListStore] = useState(() => new SessionListStore(store));

    // T-062: Rehydrate active intents + pending approvals on mount/workspace change
    useIntentRehydration(store);

    // Auto-send initialPrompt once when ChatView mounts with an empty conversation.
    // INVARIANT: `store.messages.length === 0` is the primary re-fire guard.
    // ChatView unmounts when the chat panel closes (IssueNoteLayout renders conditionally),
    // so `initialPromptFiredRef` resets on each re-open. The message-length check ensures
    // we never re-send if the store already has conversation history, even after remount.
    const initialPromptFiredRef = useRef(false);
    useEffect(() => {
      if (
        initialPrompt &&
        !initialPromptFiredRef.current &&
        store.messages.length === 0 &&
        !store.isStreaming
      ) {
        initialPromptFiredRef.current = true;
        void (store as { sendMessage: (c: string) => Promise<void> }).sendMessage(initialPrompt);
      }
    }, [initialPrompt, store]);

    // Track which note context has been loaded to avoid redundant fetches
    const loadedContextRef = useRef<string | null>(null);
    // Track if auto-resume is in progress to prevent race conditions
    const isResumingRef = useRef(false);

    // Fetch all sessions on mount for the resume menu (\resume command)
    useEffect(() => {
      sessionListStore.fetchSessions();
    }, [sessionListStore]);

    // Auto-resume most recent session for context on mount/context change.
    // Falls back to fresh conversation if no matching session exists.
    useEffect(() => {
      const noteId = store.noteContext?.noteId;

      // Skip if context hasn't changed
      if (loadedContextRef.current === noteId) {
        return;
      }

      // Update tracked context
      const previousNoteId = loadedContextRef.current;
      loadedContextRef.current = noteId ?? null;

      // If note context is cleared, clear conversation and fetch all sessions
      if (!noteId) {
        store.clearConversation();
        sessionListStore.fetchSessions();
        return;
      }

      // Note context changed - try to auto-resume existing session
      const autoResumeSession = async () => {
        if (isResumingRef.current) return;
        isResumingRef.current = true;
        setIsResumingSession(true);

        try {
          // Clear previous conversation before attempting resume
          if (previousNoteId !== null) {
            store.clearConversation();
          }

          // Try to find and resume session for this context
          const resumed = await sessionListStore.resumeSessionForContext(noteId, 'note');

          if (resumed) {
            // Session resumed - trigger scroll to bottom to show latest messages
            setScrollToBottomTrigger((prev) => prev + 1);
          } else {
            // No existing session - ensure clean state for new conversation
            store.clearConversation();
          }
        } finally {
          isResumingRef.current = false;
          setIsResumingSession(false);
        }
      };

      autoResumeSession();
    }, [store.noteContext?.noteId, sessionListStore, store]);

    // Convert TaskState to AgentTask for TaskPanel with progress data.
    // Uses MobX computed agentTaskList to avoid useMemo([store.tasks]) re-creating
    // on every observable Map mutation.
    const agentTasks: AgentTask[] = store.agentTaskList.map((task) => ({
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

    const activeAgentTasks = agentTasks.filter(
      (t) => t.status === 'pending' || t.status === 'in_progress'
    );

    const completedAgentTasks = agentTasks.filter((t) => t.status === 'completed');

    // Convert ApprovalRequest to ChatView ApprovalRequest.
    // Computed inline (no useMemo) because store.pendingApprovals is a MobX ObservableArray
    // whose reference never changes on push — useMemo([store.pendingApprovals]) would
    // cache stale empty array even after approvals arrive (observer re-renders correctly).
    const chatViewApprovals = store.pendingApprovals.map((req) => ({
      id: req.requestId,
      agentName: 'PilotSpace Agent',
      actionType: req.actionType,
      status: 'pending' as const,
      contextPreview: req.description,
      payload: req.proposedContent as Record<string, unknown> | undefined,
      createdAt: req.createdAt,
      expiresAt: req.expiresAt,
      reasoning: req.consequences,
    }));

    // Split approvals: non-destructive inline cards vs destructive modal overlay
    const inlineApprovals: typeof chatViewApprovals = [];
    const modalApprovals: typeof chatViewApprovals = [];
    for (const req of chatViewApprovals) {
      if (isDestructiveAction(req.actionType)) {
        modalApprovals.push(req);
      } else {
        inlineApprovals.push(req);
      }
    }

    // Auto-open task panel when tasks exist
    useEffect(() => {
      if (store.tasks.size > 0 && !taskPanelOpen) {
        setTaskPanelOpen(true);
      }
    }, [store.tasks.size, taskPanelOpen]);

    // Auto-open destructive approval modal when new destructive approvals arrive
    useEffect(() => {
      if (modalApprovals.length > 0) {
        setDestructiveModalOpen(true);
      }
    }, [modalApprovals.length]);

    const handleSubmit = useCallback(async () => {
      if (!inputValue.trim() || store.isStreaming) return;

      const message = inputValue.trim();
      try {
        setInputValue('');
        await store.sendMessage(message);
      } catch (error) {
        setInputValue(message);
        store.error = error instanceof Error ? error.message : 'Failed to send message';
      }
    }, [inputValue, store]);

    const handleConfirmClear = useCallback(() => {
      store.clearConversation();
      setInputValue('');
      setShowClearDialog(false);
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

    const handleSuggestedPrompt = useCallback((prompt: string) => {
      setInputValue(prompt);
    }, []);

    const handleNewSession = useCallback(() => {
      store.clear();
      setInputValue('');
    }, [store]);

    const handleSelectSession = useCallback(
      async (sessionId: string) => {
        await sessionListStore.resumeSession(sessionId);
        // Trigger scroll to bottom to show latest messages
        setScrollToBottomTrigger((prev) => prev + 1);
      },
      [sessionListStore]
    );

    // Sessions list for resume menu
    const sessionsForResumeMenu = useMemo(
      () =>
        sessionListStore.activeSessions.map((s) => ({
          sessionId: s.sessionId,
          title: s.title,
          contextHistory: s.contextHistory,
          turnCount: s.turnCount,
          updatedAt: s.updatedAt,
          agentName: s.agentName,
        })),
      [sessionListStore.activeSessions]
    );

    const handleSearchSessions = useCallback(
      (query: string) => {
        sessionListStore.searchSessions(query);
      },
      [sessionListStore]
    );

    /**
     * Load more older messages when user scrolls up.
     * Only triggers if hasMoreMessages is true.
     */
    const handleLoadMoreMessages = useCallback(async () => {
      if (!store.sessionId || !store.hasMoreMessages || store.isLoadingMoreMessages) {
        return;
      }
      await sessionListStore.loadMoreMessages(store.sessionId);
    }, [store.sessionId, store.hasMoreMessages, store.isLoadingMoreMessages, sessionListStore]);

    return (
      <div className={cn('flex flex-col h-full bg-background', className)} data-testid="chat-view">
        {/* Compact header */}
        <ChatHeader
          title="PilotSpace Agent"
          isStreaming={store.isStreaming}
          onNewSession={handleNewSession}
          onClose={onClose}
        />

        {/* Main content area - relative for floating abort button */}
        <div className="flex-1 flex flex-col overflow-hidden relative min-h-0">
          {/* T-060: Queue depth indicator — sticky top of message area */}
          <QueueDepthIndicator store={store} />

          {/* Messages or loading skeleton */}
          {isResumingSession ? (
            <ConversationLoadingSkeleton />
          ) : (
            <MessageList
              messages={store.messages}
              isStreaming={store.isStreaming}
              streamContent={store.streamContent}
              thinkingContent={store.streamingState.thinkingContent}
              thinkingBlocks={store.streamingState.thinkingBlocks}
              isThinking={store.streamingState.isThinking}
              thinkingStartedAt={store.streamingState.thinkingStartedAt}
              interrupted={store.streamingState.interrupted}
              pendingToolCalls={store.pendingToolCalls}
              blockOrder={store.streamingState.blockOrder}
              textSegments={store.streamingState.textSegments}
              userName={userName}
              userAvatar={userAvatar}
              className="flex-1"
              scrollToBottomTrigger={scrollToBottomTrigger}
              hasMoreMessages={store.hasMoreMessages}
              isLoadingMoreMessages={store.isLoadingMoreMessages}
              onLoadMore={handleLoadMoreMessages}
              onSuggestedPrompt={handleSuggestedPrompt}
              suggestedPrompts={suggestedPrompts}
              emptyStateSlot={emptyStateSlot}
              streamingPhase={store.streamingState.phase}
              activeToolName={store.streamingState.activeToolName}
              wordCount={store.streamingState.wordCount ?? 0}
            />
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

          {/* T-056/T-057: Intent lifecycle message renderer */}
          {store.intents.size > 0 && (
            <IntentMessageRenderer store={store} onPrefillInput={setInputValue} />
          )}

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
                role="alert"
                className="rounded-lg border border-destructive/50 bg-destructive/10 p-2.5 flex items-start gap-2"
                data-testid="error-message"
              >
                <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
                <p className="text-xs text-destructive flex-1">{store.error}</p>
                <button
                  type="button"
                  onClick={() => {
                    store.error = null;
                  }}
                  className="p-1.5 -m-1.5 text-destructive/60 hover:text-destructive shrink-0"
                  aria-label="Dismiss error"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Inline approval cards for non-destructive approvals */}
        {inlineApprovals.map((approval) => (
          <InlineApprovalCard
            key={approval.id}
            approval={approval}
            onApprove={handleApproveAction}
            onReject={handleRejectAction}
          />
        ))}

        {/* Waiting indicator — shown when agent is blocked on user input */}
        {store.isWaitingForUser && (
          <WaitingIndicator waitingType={store.pendingQuestion ? 'question' : 'approval'} />
        )}

        {/* Streaming phase is now shown inline in MessageList */}

        {/* T-059: ConfirmAll button — above ChatInput when >= 2 pending intents */}
        <ConfirmAllButton store={store} />

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
                  projectId: store.issueContext.projectId ?? '',
                  title: store.issueContext.issueTitle || '',
                  description: '',
                }
              : null
          }
          projectContext={null}
          tokenBudgetPercent={store.tokenBudgetPercent}
          tokensUsed={store.sessionState?.totalTokens}
          tokenBudget={8000}
          sessions={sessionsForResumeMenu}
          sessionsLoading={sessionListStore.isLoading}
          onSelectSession={handleSelectSession}
          onSearchSessions={handleSearchSessions}
          onNewSession={handleNewSession}
          onClearNoteContext={handleClearNoteContext}
          onClearIssueContext={handleClearIssueContext}
          onClearProjectContext={handleClearProjectContext}
        />

        {/* Modal for destructive actions — non-dismissable (DD-003) */}
        <DestructiveApprovalModal
          approval={modalApprovals[0] ?? null}
          isOpen={destructiveModalOpen && modalApprovals.length > 0}
          onApprove={handleApproveAction}
          onReject={handleRejectAction}
          onClose={() => setDestructiveModalOpen(false)}
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
