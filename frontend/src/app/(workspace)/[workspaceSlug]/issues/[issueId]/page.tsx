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
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { DestructiveApprovalModal } from '@/features/ai/ChatView/ApprovalOverlay/DestructiveApprovalModal';

import {
  IssueNoteHeader,
  IssueNoteLayout,
  IssuePropertiesPanel,
  ActionButtonBar,
} from '@/features/issues/components';
import { ProjectContextHeader } from '@/components/editor/ProjectContextHeader';
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
import { implementationPlanKeys } from '@/features/issues/hooks/use-implementation-plan';
import { useIssueApprovals } from '@/features/issues/hooks/use-issue-approvals';
import { useIssueAiActions } from '@/features/issues/hooks/use-issue-ai-actions';
import { IssueNoteContext } from '@/features/issues/contexts/issue-note-context';
import { useStore } from '@/stores';
import { copyToClipboard } from '@/lib/copy-context';
import { issuesApi, tasksApi } from '@/services/api';
import { useActionButtons } from '@/services/api/skill-action-buttons';
import type { ExportFormat } from '@/features/issues/components';
import type { UpdateIssueData, IssueState, UserBrief } from '@/types';
import { IssueChatEmptyState } from '@/features/issues/components/issue-chat-empty-state';
import type { AIContextResult } from '@/stores/ai/AIContextStore';
// RightPanelTab type removed — graph tab no longer in issue right panel

import '@/features/notes/editor/extensions/note-link.css';

// ---------------------------------------------------------------------------
// Typed accessor for aiStore.pilotSpace (replaces unsafe `as` casts)
// ---------------------------------------------------------------------------
interface IssuePagePilotSpaceAPI {
  sendMessage: (content: string) => Promise<void>;
  isStreaming: boolean;
  clearConversation: () => void;
  setIssueContext: (ctx: { issueId: string } | null) => void;
  setWorkspaceId: (id: string | null) => void;
  setActiveSkill: (skill: string) => void;
  approveRequest: (id: string) => Promise<void>;
  rejectRequest: (id: string, reason: string) => Promise<void>;
  pendingApprovals?: Array<{
    requestId: string;
    actionType: string;
    description: string;
    consequences?: string;
    proposedContent?: unknown;
    createdAt: Date;
    expiresAt: Date;
    affectedEntities: Array<{ type: string; id: string }>;
  }>;
}

// ---------------------------------------------------------------------------
// Lazy-loaded heavy components
// ---------------------------------------------------------------------------
// IssueKnowledgeGraphFull removed — full view navigates to project graph page

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
  const pilotSpace = aiStore.pilotSpace as unknown as IssuePagePilotSpaceAPI;
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;
  const queryClient = useQueryClient();

  // -- TanStack Query hooks --
  const { data: issue, isLoading, isError, refetch } = useIssueDetail(workspaceId, issueId);
  const updateIssue = useUpdateIssue(workspaceId, issueId);
  const updateIssueState = useUpdateIssueState(workspaceId, issueId);
  const { data: membersData } = useWorkspaceMembers(workspaceId);
  const members = membersData?.items ?? [];
  const { data: labels = [] } = useWorkspaceLabels(workspaceId);
  const { data: cyclesData } = useProjectCycles(workspaceId, issue?.project?.id ?? '');
  const { data: actionButtons } = useActionButtons(workspaceId);

  // -- UI state --
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [mobilePropertiesOpen, setMobilePropertiesOpen] = useState(false);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [editorKey, setEditorKey] = useState(0);

  // -- Right panel tab state --
  // Graph tab removed — full graph view navigates to project/workspace page

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
      void queryClient.invalidateQueries({
        queryKey: implementationPlanKeys.detail(issueId),
      });
    } catch {
      toast.error('Failed to generate plan', {
        description: 'Ensure AI context is generated first, then try again.',
      });
    } finally {
      setIsGeneratingPlan(false);
    }
  }, [workspaceId, issueId, queryClient]);

  // -- AI action handlers (extracted to hook) --
  const { handleChatSend, handleAiGenerateFromEditor, handleActionButtonClick } = useIssueAiActions(
    {
      pilotSpace,
      issueId,
      setIsChatOpen,
    }
  );

  // -- Knowledge graph handlers --

  /** Called by mini-graph "Expand full view" → navigate to project knowledge graph */
  const handleExpandGraphFullView = useCallback(() => {
    if (issue?.projectId) {
      router.push(`/${workspaceSlug}/projects/${issue.projectId}/knowledge`);
    } else {
      // No project — navigate to workspace knowledge graph
      router.push(`/${workspaceSlug}/knowledge`);
    }
  }, [issue?.projectId, router, workspaceSlug]);

  // handleNodeClickHighlight removed — graph tab no longer in issue right panel

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
    pilotSpace.setWorkspaceId(workspaceId);
    pilotSpace.setIssueContext({ issueId });
    return () => {
      pilotSpace.setIssueContext(null);
    };
  }, [workspaceId, issueId, pilotSpace]);

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

  // -- DD-003: Approval flow (extracted to hook) --
  const {
    destructiveApproval,
    destructiveModalOpen,
    setDestructiveModalOpen,
    handleApproveAction,
    handleRejectAction,
  } = useIssueApprovals(pilotSpace, issueId, setIsChatOpen);

  // -- IssueNoteContext value --
  const contextValue = useMemo(
    () =>
      issue
        ? {
            issue,
            members: memberUsers,
            labels,
            cycles,
            onUpdate: handleUpdate,
            onUpdateState: handleUpdateState,
            disabled: false,
          }
        : null,
    [issue, memberUsers, labels, cycles, handleUpdate, handleUpdateState]
  );

  // -- Render states --
  if (isLoading) return <IssueDetailSkeleton />;
  if (isError || !issue || !contextValue) return <IssueNotFound onBack={handleBack} />;

  // -- AI context result + chat empty state --
  const aiContextResult =
    (aiStore.aiContext as unknown as { result: AIContextResult | null } | undefined)?.result ??
    null;

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
      onExpandGraphFullView={handleExpandGraphFullView}
      onNodeClickHighlight={undefined}
    />
  );

  const header = (
    <>
      {issue.projectId && (
        <ProjectContextHeader
          projectId={issue.projectId}
          workspaceSlug={workspaceSlug}
          activeTab="issues"
        />
      )}
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
      <ActionButtonBar buttons={actionButtons ?? []} onButtonClick={handleActionButtonClick} />
    </>
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
