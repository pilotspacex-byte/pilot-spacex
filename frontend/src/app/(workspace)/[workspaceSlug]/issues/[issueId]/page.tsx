'use client';

/**
 * IssueDetailPage - Note-first issue detail view.
 *
 * Architecture (mirrors NoteCanvasLayout pattern):
 *   IssueDetailPage (observer) → data fetching, MobX reactivity
 *     └─ IssueEditorContent (NOT observer) → useEditor + EditorContent
 *         └─ PropertyBlockView (observer) → isolated child reactivity
 *
 * This separation prevents MobX's useSyncExternalStore from calling flushSync
 * during the same render cycle as TipTap's ReactNodeViewRenderer.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { DestructiveApprovalModal } from '@/features/ai/ChatView/ApprovalOverlay/DestructiveApprovalModal';
import { isDestructiveAction } from '@/features/ai/ChatView/ChatView';

import {
  IssueNoteHeader,
  IssueNoteLayout,
  IssuePropertiesPanel,
} from '@/features/issues/components';
import { IssueEditorContent } from '@/features/issues/components/issue-editor-content';
import { DeleteConfirmDialog } from '@/components/issues/DeleteConfirmDialog';
import {
  useIssueDetail,
  useUpdateIssue,
  useUpdateIssueState,
  useWorkspaceMembers,
  useWorkspaceLabels,
  useProjectCycles,
  useIssueKeyboardShortcuts,
} from '@/features/issues/hooks';
import { IssueNoteContext } from '@/features/issues/contexts/issue-note-context';
import { useStore } from '@/stores';
import { copyToClipboard } from '@/lib/copy-context';
import { issuesApi, tasksApi } from '@/services/api';
import type { ExportFormat } from '@/features/issues/components';
import type { UpdateIssueData, IssueState, UserBrief } from '@/types';
import { IssueChatEmptyState } from '@/features/issues/components/issue-chat-empty-state';
import type { AIContextResult } from '@/stores/ai/AIContextStore';

import '@/features/notes/editor/extensions/note-link.css';

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function IssueDetailSkeleton() {
  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: header + editor */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex items-center gap-4 border-b px-4 h-12 shrink-0">
          <Skeleton className="h-6 w-6" />
          <Skeleton className="h-5 w-32" />
          <div className="flex-1" />
          <Skeleton className="h-6 w-6" />
        </div>
        <div className="flex-1 space-y-4 p-8">
          <Skeleton className="h-10 w-full max-w-md rounded-[12px]" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
      {/* Right: chat (full height, no header above it) */}
      <div className="w-[38%] hidden lg:flex border-l flex-col p-4 gap-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

function IssueNotFound({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <p className="text-lg font-medium">Issue not found</p>
      <Button variant="link" onClick={onBack}>
        Back to issues
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component (observer-wrapped for MobX store access)
// ---------------------------------------------------------------------------
const IssueDetailPage = observer(function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const issueId = params.issueId as string;

  const { workspaceStore, issueStore, aiStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  // -- TanStack Query hooks --
  const { data: issue, isLoading, isError, refetch } = useIssueDetail(workspaceId, issueId);
  const updateIssue = useUpdateIssue(workspaceId, issueId);
  const updateIssueState = useUpdateIssueState(workspaceId, issueId);
  const { data: members = [] } = useWorkspaceMembers(workspaceId);
  const { data: labels = [] } = useWorkspaceLabels(workspaceId);
  const { data: cyclesData } = useProjectCycles(workspaceId, issue?.project?.id ?? '');

  // -- UI state --
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [mobilePropertiesOpen, setMobilePropertiesOpen] = useState(false);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [editorKey, setEditorKey] = useState(0);

  // -- Derived data --
  const memberUsers = useMemo<UserBrief[]>(() => {
    const seen = new Set<string>();
    return members
      .filter((m) => {
        if (!m.userId || seen.has(m.userId)) return false;
        seen.add(m.userId);
        return true;
      })
      .map((m) => ({
        id: m.userId,
        email: m.email,
        displayName: m.fullName ?? null,
      }));
  }, [members]);

  const cycles = useMemo(() => cyclesData?.items ?? [], [cyclesData]);

  // -- Handlers --
  const handleBack = useCallback(() => {
    router.push(`/${workspaceSlug}/issues`);
  }, [router, workspaceSlug]);

  const handleUpdate = useCallback(
    (data: UpdateIssueData) => updateIssue.mutateAsync(data),
    [updateIssue]
  );

  const handleUpdateState = useCallback(
    (state: IssueState) => updateIssueState.mutateAsync(state),
    [updateIssueState]
  );

  const handleCopyLink = useCallback(() => {
    void copyToClipboard(window.location.href);
  }, []);

  const handleDeleteClick = useCallback(() => {
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!workspaceId || !issue?.id) return;
    setIsDeleting(true);
    try {
      await issueStore.deleteIssue(workspaceId, issue.id);
      setDeleteDialogOpen(false);
      router.push(`/${workspaceSlug}/issues`);
    } catch {
      toast.error('Failed to delete issue', {
        description: 'Please try again or contact support if the problem persists.',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [workspaceId, issue?.id, issueStore, router, workspaceSlug]);

  const handleToggleChat = useCallback(() => {
    setIsChatOpen((prev) => !prev);
  }, []);

  const handleChatOpen = useCallback(() => setIsChatOpen(true), []);
  const handleChatClose = useCallback(() => setIsChatOpen(false), []);

  const handleExportContext = useCallback(
    async (format: ExportFormat): Promise<string | null> => {
      try {
        if (format === 'implementation_plan') {
          const result = await issuesApi.exportAiContext(issueId, 'implementation_plan');
          return result.content;
        }
        const result = await tasksApi.exportContext(workspaceId, issueId, format);
        return result.content;
      } catch {
        return null;
      }
    },
    [workspaceId, issueId]
  );

  const handleGeneratePlan = useCallback(async () => {
    setIsGeneratingPlan(true);
    try {
      const result = await issuesApi.generatePlan(workspaceId, issueId);
      toast.success('Implementation plan generated', {
        description: `Plan with ${result.subagentCount} subagent${result.subagentCount !== 1 ? 's' : ''} ready. Open Clone → Plan tab to copy.`,
      });
    } catch {
      toast.error('Failed to generate plan', {
        description: 'Ensure AI context is generated first, then try again.',
      });
    } finally {
      setIsGeneratingPlan(false);
    }
  }, [workspaceId, issueId]);

  const handleChatSend = useCallback(
    (prompt: string) => {
      void (aiStore.pilotSpace as { sendMessage: (c: string) => Promise<void> }).sendMessage(
        prompt
      );
    },
    [aiStore.pilotSpace]
  );

  // Opens chat AND immediately sends the generate-description prompt.
  // Used by the editor empty state CTA so the button has a visible effect
  // even when the chat panel is already open (isChatOpen defaults to true).
  // Guard: no-op if the store is already streaming (prevents duplicate sends).
  const handleAiGenerateFromEditor = useCallback(() => {
    const store = aiStore.pilotSpace as {
      sendMessage: (c: string) => Promise<void>;
      isStreaming: boolean;
    };
    if (store.isStreaming) return;
    setIsChatOpen(true);
    handleChatSend(
      `Generate a detailed description for this issue. Structure it with: Problem statement, Acceptance criteria, and Technical approach.`
    );
  }, [handleChatSend, aiStore.pilotSpace]);

  // -- Keyboard shortcuts --
  const handleForceSave = useCallback(() => {
    document.dispatchEvent(new CustomEvent('issue-force-save'));
  }, []);

  useIssueKeyboardShortcuts({
    onForceSave: handleForceSave,
  });

  // -- Initialise PilotSpaceStore context so chat includes workspace + issue --
  // Both conversationContext (chat body) and X-Workspace-Id (sessions header)
  // depend on these being set.
  useEffect(() => {
    const store = aiStore.pilotSpace as {
      setWorkspaceId: (id: string | null) => void;
      setIssueContext: (ctx: { issueId: string } | null) => void;
    };
    store.setWorkspaceId(workspaceId);
    store.setIssueContext({ issueId });
    return () => {
      store.setIssueContext(null);
    };
  }, [workspaceId, issueId, aiStore.pilotSpace]);

  // -- Refetch issue when AI agent applies an update, then remount editor --
  useEffect(() => {
    const handler = async (e: Event) => {
      const { issueId: updatedId } = (e as CustomEvent<{ issueId?: string }>).detail;
      if (updatedId !== issueId) return;
      const result = await refetch();
      // Only remount on success — a failed refetch (e.g. expired session) would
      // remount with stale data and show no change to the user.
      if (result.status === 'success') {
        // Increment key to force IssueEditorContent remount with fresh issue data.
        // useEditor's `content` option only applies at mount time.
        setEditorKey((k) => k + 1);
      }
    };
    window.addEventListener('pilot:issue-updated', handler);
    return () => window.removeEventListener('pilot:issue-updated', handler);
  }, [issueId, refetch]);

  // ⇧⌘C / Shift+Ctrl+C — quick copy claude_code context
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta || !e.shiftKey || e.key !== 'c') return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      e.preventDefault();
      const content = await handleExportContext('claude_code');
      if (!content) return;
      try {
        await navigator.clipboard.writeText(content);
      } catch {
        /* ignore */
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [handleExportContext]);

  // -- DD-003: Approval flow --
  // Map store approval shape to ChatView ApprovalRequest shape.
  const issueApprovals = useMemo(() => {
    return (
      (aiStore.pilotSpace as { pendingApprovals?: unknown[] }).pendingApprovals
        ?.filter(
          (r): r is NonNullable<typeof r> =>
            r !== null &&
            typeof r === 'object' &&
            'affectedEntities' in r &&
            Array.isArray((r as { affectedEntities: unknown[] }).affectedEntities) &&
            (r as { affectedEntities: Array<{ type: string; id: string }> }).affectedEntities.some(
              (e) => e.type === 'issue' && e.id === issueId
            )
        )
        .map((r) => {
          const req = r as {
            requestId: string;
            actionType: string;
            description: string;
            consequences?: string;
            proposedContent?: unknown;
            createdAt: Date;
            expiresAt: Date;
          };
          return {
            id: req.requestId,
            agentName: 'PilotSpace Agent',
            actionType: req.actionType,
            status: 'pending' as const,
            contextPreview: req.description,
            payload: req.proposedContent as Record<string, unknown> | undefined,
            createdAt: req.createdAt,
            expiresAt: req.expiresAt,
            reasoning: req.consequences,
          };
        }) ?? []
    );
  }, [(aiStore.pilotSpace as { pendingApprovals?: unknown[] }).pendingApprovals, issueId]);

  const destructiveApproval = useMemo(
    () => issueApprovals.find((a) => isDestructiveAction(a.actionType)) ?? null,
    [issueApprovals]
  );

  const [destructiveModalOpen, setDestructiveModalOpen] = useState(false);

  // Auto-open chat for non-destructive approvals; open modal for destructive ones.
  useEffect(() => {
    if (issueApprovals.length === 0) return;
    if (destructiveApproval) {
      setDestructiveModalOpen(true);
    } else {
      setIsChatOpen(true);
    }
  }, [issueApprovals.length, destructiveApproval]);

  const handleApproveAction = useCallback(
    async (id: string) => {
      await (
        aiStore.pilotSpace as { approveRequest: (id: string) => Promise<void> }
      ).approveRequest(id);
    },
    [aiStore.pilotSpace]
  );

  const handleRejectAction = useCallback(
    async (id: string, reason: string) => {
      await (
        aiStore.pilotSpace as { rejectRequest: (id: string, reason: string) => Promise<void> }
      ).rejectRequest(id, reason);
    },
    [aiStore.pilotSpace]
  );

  // -- Render states --
  if (isLoading) return <IssueDetailSkeleton />;
  if (isError || !issue) return <IssueNotFound onBack={handleBack} />;

  // -- AI context result + chat empty state --
  const aiContextResult =
    (aiStore.aiContext as { result: AIContextResult | null } | undefined)?.result ?? null;

  const chatEmptyState = issue ? (
    <IssueChatEmptyState
      issue={issue}
      aiContextResult={aiContextResult}
      workspaceSlug={workspaceSlug}
      onSendPrompt={handleChatSend}
    />
  ) : undefined;

  const initialPrompt =
    !issue?.description && isChatOpen
      ? `Generate a detailed description for this issue. Structure it with: Problem statement, Acceptance criteria, and Technical approach.`
      : undefined;

  // -- IssueNoteContext value --
  const contextValue = {
    issue,
    members: memberUsers,
    labels,
    cycles,
    onUpdate: handleUpdate,
    onUpdateState: handleUpdateState,
    disabled: false,
  };

  // -- Editor content (non-observer component to avoid flushSync) --
  const editorContent = (
    <IssueEditorContent
      key={editorKey}
      issue={issue}
      issueId={issueId}
      workspaceId={workspaceId}
      workspaceSlug={workspaceSlug}
      onUpdate={handleUpdate}
      onChatOpen={handleChatOpen}
      onAiGenerate={handleAiGenerateFromEditor}
    />
  );

  const header = (
    <IssueNoteHeader
      identifier={issue.identifier}
      issueTitle={issue.name}
      issueType={issue.type}
      aiGenerated={issue.aiGenerated ?? false}
      isChatOpen={isChatOpen}
      onBack={handleBack}
      onToggleChat={handleToggleChat}
      onCopyLink={handleCopyLink}
      onDelete={handleDeleteClick}
      onExport={handleExportContext}
      onGeneratePlan={handleGeneratePlan}
      isGeneratingPlan={isGeneratingPlan}
    />
  );

  return (
    <IssueNoteContext.Provider value={contextValue}>
      <div className="flex h-full bg-background overflow-hidden" data-testid="issue-detail">
        <IssueNoteLayout
          headerContent={header}
          editorContent={editorContent}
          aiStore={aiStore}
          isChatOpen={isChatOpen}
          onChatOpen={handleChatOpen}
          onChatClose={handleChatClose}
          emptyStateSlot={chatEmptyState}
          initialPrompt={initialPrompt}
        />

        <Sheet open={mobilePropertiesOpen} onOpenChange={setMobilePropertiesOpen}>
          <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
            <SheetHeader>
              <SheetTitle>Properties</SheetTitle>
            </SheetHeader>
            {mobilePropertiesOpen && (
              <IssuePropertiesPanel
                issue={issue}
                workspaceId={workspaceId}
                workspaceSlug={workspaceSlug}
                members={members}
                labels={labels}
                cycles={cycles}
                onUpdate={handleUpdate}
              />
            )}
          </SheetContent>
        </Sheet>

        <DeleteConfirmDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          issues={[issue]}
          onConfirm={handleDeleteConfirm}
          isDeleting={isDeleting}
        />

        <DestructiveApprovalModal
          approval={destructiveApproval}
          isOpen={destructiveModalOpen}
          onApprove={handleApproveAction}
          onReject={handleRejectAction}
          onClose={() => setDestructiveModalOpen(false)}
        />
      </div>
    </IssueNoteContext.Provider>
  );
});

export default IssueDetailPage;
