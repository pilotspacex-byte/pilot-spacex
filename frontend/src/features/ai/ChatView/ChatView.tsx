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

import type { HeadingItem } from '@/components/editor/AutoTOC';
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
import { Button } from '@/components/ui/button';
import { FilePreviewModal } from '@/features/artifacts/components/FilePreviewModal';
import { cn } from '@/lib/utils';
import { useWorkspaceStore } from '@/stores';
import type { ApprovalStore } from '@/stores/ai/ApprovalStore';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import { AlertCircle, Square, X } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DestructiveApprovalModal } from './ApprovalOverlay/DestructiveApprovalModal';
import { ChatHeader } from './ChatHeader';
import { ChatInput } from './ChatInput/ChatInput';
import { ChatViewErrorBoundary } from './ChatViewErrorBoundary';
import { ConfirmAllButton } from './ConfirmAllButton';
import { ApprovalCardGroup } from './MessageList/ApprovalCardGroup';
import { ConversationLoadingSkeleton } from './MessageList/ConversationLoadingSkeleton';
import { InlineApprovalCard } from './MessageList/InlineApprovalCard';
import { IntentMessageRenderer } from './MessageList/IntentMessageRenderer';
import { MessageList } from './MessageList/MessageList';
import { QueueDepthIndicator } from './QueueDepthIndicator';
import { TaskPanel } from './TaskPanel/TaskPanel';
import { WaitingIndicator } from './WaitingIndicator';
import { useApprovals } from './hooks/useApprovals';
import { useAttachmentPreview } from './hooks/useAttachmentPreview';
import { useIntentRehydration } from './hooks/useIntentRehydration';
import { SkillCreatorCard } from './MessageList/SkillCreatorCard';
import { userSkillsApi } from '@/services/api/user-skills';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import type { AgentTask } from './types';
export { isDestructiveAction } from './utils';

interface ChatViewProps {
  store: PilotSpaceStore;
  /** Backend-polled approval store — loads all pending approvals across sessions */
  approvalStore?: ApprovalStore;
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
  /** Pre-fill the input field without auto-sending (e.g., from ?prefill= query param) */
  prefillValue?: string;
  /** Headings from the current note for # section mentions in ChatInput */
  noteHeadings?: HeadingItem[];
  /** Callback when user selects a section via # menu — sets note context to section blocks */
  onSelectSection?: (heading: HeadingItem) => void;
  /** When true, don't auto-resume/clear conversations on context changes.
   *  Used by ChatFirstShell's persistent ChatView which lives across page navigations. */
  persistentMode?: boolean;
  className?: string;
}

const ChatViewInternal = observer<ChatViewProps>(
  ({
    store,
    approvalStore,
    userName,
    userAvatar,
    autoFocus,
    onClose,
    suggestedPrompts,
    emptyStateSlot,
    initialPrompt,
    prefillValue,
    noteHeadings,
    onSelectSection,
    persistentMode,
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

    // Skill card save state — pinned above ChatInput
    const workspaceStore = useWorkspaceStore();
    const queryClient = useQueryClient();
    const [isSkillSaving, setIsSkillSaving] = useState(false);
    const [isSkillSaved, setIsSkillSaved] = useState(false);

    // Reset saved state when a new skill preview arrives
    const skillPreviewRef = useRef(store.skillPreview);
    if (store.skillPreview !== skillPreviewRef.current) {
      skillPreviewRef.current = store.skillPreview;
      if (store.skillPreview) {
        setIsSkillSaved(false);
      }
    }

    const handleSkillCardSave = useCallback(
      async (content: string) => {
        const slug = workspaceStore.currentWorkspace?.slug;
        const skillName = store.skillPreview?.skillName;
        if (!slug || !skillName) return;
        setIsSkillSaving(true);
        try {
          await userSkillsApi.createUserSkill(slug, {
            skill_name: skillName,
            skill_content: content,
          });
          toast.success(`Skill "${skillName}" saved to your workspace`);
          setIsSkillSaved(true);
          void queryClient.invalidateQueries({ queryKey: ['user-skills', slug] });
        } catch (err) {
          toast.error(err instanceof Error ? err.message : 'Failed to save skill');
        } finally {
          setIsSkillSaving(false);
        }
      },
      [store, workspaceStore, queryClient]
    );

    const handleSkillCardTest = useCallback(
      (_content: string) => {
        const skillName = store.skillPreview?.skillName;
        if (!skillName) return;
        void store.sendMessage(`\\${skillName} analyze this sample.`);
      },
      [store]
    );

    // Attachment preview — opens FilePreviewModal when AttachmentChip is clicked
    const attachmentPreview = useAttachmentPreview();

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

    // Pre-fill the input field from prefillValue prop (e.g., ?prefill=/skill-creator).
    // Only applies when input is empty to avoid overwriting user's in-progress text.
    const lastPrefillRef = useRef<string | null>(null);
    useEffect(() => {
      if (prefillValue && prefillValue !== lastPrefillRef.current) {
        lastPrefillRef.current = prefillValue;
        // Only prefill if user hasn't typed anything
        if (!inputValue.trim()) {
          setInputValue(prefillValue);
        }
      }
    }, [prefillValue, inputValue]);

    // Track which note context has been loaded to avoid redundant fetches
    const loadedContextRef = useRef<string | null>(null);
    // Track if auto-resume is in progress to prevent race conditions
    const isResumingRef = useRef(false);

    // Fetch all sessions on mount for the resume menu (\resume command)
    useEffect(() => {
      sessionListStore.fetchSessions();
    }, [sessionListStore]);

    // Load all backend-pending approvals on mount, then poll every 30s.
    // De-duplicated with SSE arrivals in chatViewApprovals derivation below.
    useEffect(() => {
      if (!approvalStore) return;
      void approvalStore.loadPending();
      const interval = setInterval(() => void approvalStore.loadPending(), 30_000);
      return () => clearInterval(interval);
    }, [approvalStore]);

    // Auto-resume most recent session for context on mount/context change.
    // Falls back to fresh conversation if no matching session exists.
    // Skipped in persistentMode (ChatFirstShell's persistent ChatView).
    useEffect(() => {
      if (persistentMode) return;

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

      // If the store already has messages for the same note context (e.g. chat panel
      // was closed and reopened), preserve the conversation instead of re-fetching.
      if (previousNoteId === null && store.messages.length > 0) {
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
    }, [store.noteContext?.noteId, sessionListStore, store, persistentMode]);

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

    // Derive inline / modal approval lists from SSE + polled sources.
    // useApprovals must be called inside observer() — MobX auto-tracks the
    // store.pendingApprovals ObservableArray accesses made in the hook.
    const { inlineApprovals, modalApprovals } = useApprovals(store, approvalStore);

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

    const handleSubmit = useCallback(
      async (payload: {
        attachmentIds: string[];
        attachments: Array<{ attachmentId: string; filename: string; mimeType: string; sizeBytes: number; source: 'local' | 'google_drive' }>;
        voiceAudioUrl?: string | null;
      }) => {
        if (!inputValue.trim() || store.isStreaming) return;

        const message = inputValue.trim();
        try {
          setInputValue('');
          const hasAttachments = payload.attachments.length > 0;
          const hasVoice = !!payload.voiceAudioUrl;
          const metadata = hasAttachments || hasVoice
            ? {
                ...(hasVoice ? { voiceAudioUrl: payload.voiceAudioUrl } : {}),
                ...(hasAttachments ? { attachments: payload.attachments } : {}),
              }
            : undefined;
          await store.sendMessage(message, metadata, payload.attachmentIds);
        } catch (error) {
          setInputValue(message);
          store.error = error instanceof Error ? error.message : 'Failed to send message';
        }
      },
      [inputValue, store]
    );

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
        if (approvalStore) {
          await approvalStore.approve(id);
          store.removePendingApproval(id);
        } else {
          await store.approveAction(id, modifications);
        }
      },
      [store, approvalStore]
    );

    const handleRejectAction = useCallback(
      async (id: string, reason: string) => {
        if (approvalStore) {
          await approvalStore.reject(id, reason);
          store.removePendingApproval(id);
        } else {
          await store.rejectAction(id, reason);
        }
      },
      [store, approvalStore]
    );

    const handleSuggestedPrompt = useCallback(
      async (prompt: string) => {
        // Auto-send suggested prompts immediately (Claude.ai pattern)
        try {
          await store.sendMessage(prompt);
        } catch (error) {
          // Fallback: prefill input so user can retry manually
          setInputValue(prompt);
          store.error = error instanceof Error ? error.message : 'Failed to send message';
        }
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

        {/* Inline approval cards — batch group for 3+, animated list otherwise */}
        {inlineApprovals.length >= 3 ? (
          <ApprovalCardGroup
            approvals={inlineApprovals}
            onApprove={handleApproveAction}
            onReject={handleRejectAction}
          />
        ) : (
          <AnimatePresence mode="popLayout">
            {inlineApprovals.map((approval) => (
              <motion.div
                key={approval.id}
                layout
                exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.97 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
              >
                <InlineApprovalCard
                  approval={approval}
                  onApprove={handleApproveAction}
                  onReject={handleRejectAction}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        )}

        {/* Waiting indicator — shown when agent is blocked on user input */}
        {store.isWaitingForUser && (
          <WaitingIndicator waitingType={store.pendingQuestion ? 'question' : 'approval'} />
        )}

        {/* Streaming phase is now shown inline in MessageList */}

        {/* T-059: ConfirmAll button — above ChatInput when >= 2 pending intents */}
        <ConfirmAllButton store={store} />

        {/* Skill creator card — pinned above input for easy Save/Test access.
            Hidden while streaming so it disappears during updates and reappears
            with fresh content when the new skill_preview event arrives. */}
        {store.skillPreview && !store.isStreaming && (
          <div className="border-t border-border bg-background">
            <SkillCreatorCard
              skillName={store.skillPreview.skillName}
              frontmatter={store.skillPreview.frontmatter}
              content={store.skillPreview.content}
              isUpdate={store.skillPreview.isUpdate}
              onSave={handleSkillCardSave}
              onTest={handleSkillCardTest}
              isSaving={isSkillSaving}
              isSaved={isSkillSaved}
            />
          </div>
        )}

        {/* Input */}
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          autoFocus={autoFocus}
          isStreaming={store.isStreaming}
          isDisabled={store.hasUnresolvedApprovals}
          workspaceId={store.workspaceId ?? ''}
          sessionId={store.sessionId ?? undefined}
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
          projectContext={
            store.projectContext
              ? {
                  projectId: store.projectContext.projectId,
                  name: store.projectContext.name ?? '',
                  identifier: store.projectContext.slug ?? '',
                }
              : null
          }
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
          noteHeadings={noteHeadings}
          onSelectSection={onSelectSection}
        />

        {/* Modal for destructive actions — non-dismissable (DD-003) */}
        <DestructiveApprovalModal
          approval={modalApprovals[0] ?? null}
          isOpen={destructiveModalOpen && modalApprovals.length > 0}
          onApprove={handleApproveAction}
          onReject={handleRejectAction}
          onClose={() => setDestructiveModalOpen(false)}
          totalCount={modalApprovals.length}
        />

        {/* Screen reader announcement region for new approvals (P2 aria-live) */}
        <div aria-live="polite" aria-atomic="true" className="sr-only">
          {inlineApprovals.length > 0
            ? `${inlineApprovals.length} pending approval${inlineApprovals.length === 1 ? '' : 's'} require your attention`
            : ''}
        </div>

        {/* File preview modal — opens when AttachmentChip is clicked */}
        {attachmentPreview.signedUrl && <FilePreviewModal {...attachmentPreview} />}

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
