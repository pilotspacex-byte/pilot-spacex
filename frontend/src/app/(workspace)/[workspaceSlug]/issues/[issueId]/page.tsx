'use client';

/**
 * IssueDetailPage - Single issue view with properties panel and activity timeline.
 *
 * T043: Refactored to use TanStack Query hooks for data fetching and compose
 * child components (IssueTitle, IssueDescriptionEditor, SubIssuesList,
 * ActivityTimeline, IssuePropertiesPanel) instead of inline JSX.
 *
 * MobX is retained only for UI-only stores (workspaceStore, aiStore).
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { toast } from 'sonner';
import { ClipboardList, MessageSquare, SlidersHorizontal, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  IssueHeader,
  IssueTitle,
  IssueDescriptionEditor,
  SubIssuesList,
  ActivityTimeline,
  IssuePropertiesPanel,
  AcceptanceCriteriaEditor,
  TechnicalRequirementsEditor,
  CollapsibleSection,
  TaskProgressWidget,
} from '@/features/issues/components';
import { DeleteConfirmDialog } from '@/components/issues/DeleteConfirmDialog';
import {
  useIssueDetail,
  useUpdateIssue,
  useWorkspaceMembers,
  useWorkspaceLabels,
  useProjectCycles,
  useIssueKeyboardShortcuts,
} from '@/features/issues/hooks';
import { useStore } from '@/stores';
import { copyToClipboard } from '@/lib/copy-context';
import type { UpdateIssueData } from '@/types';

const AIContextTab = dynamic(
  () =>
    import('@/features/issues/components/ai-context-tab').then((mod) => ({
      default: mod.AIContextTab,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center py-12">
        <Skeleton className="h-8 w-48" />
      </div>
    ),
  }
);

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function IssueDetailSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-4 border-b px-6 py-4">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-6 w-48" />
      </div>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 space-y-4 p-6">
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
        <div className="w-80 shrink-0 space-y-4 border-l p-6">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error / not-found state
// ---------------------------------------------------------------------------

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
// Main page component
// ---------------------------------------------------------------------------

const IssueDetailPage = observer(function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const issueId = params.issueId as string;

  const { workspaceStore, issueStore } = useStore();
  // Backend accepts both UUID and slug — use slug as fallback when store isn't hydrated
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  // -- TanStack Query hooks --------------------------------------------------
  const { data: issue, isLoading, isError } = useIssueDetail(workspaceId, issueId);
  const updateIssue = useUpdateIssue(workspaceId, issueId);
  const { data: members = [] } = useWorkspaceMembers(workspaceId);
  const { data: labels = [] } = useWorkspaceLabels(workspaceId);
  const { data: cyclesData } = useProjectCycles(workspaceId, issue?.project?.id ?? '');

  // -- Keyboard shortcuts (T045) ---------------------------------------------
  const handleForceSave = React.useCallback(() => {
    document.dispatchEvent(new CustomEvent('issue-force-save'));
  }, []);

  useIssueKeyboardShortcuts({
    onForceSave: handleForceSave,
  });

  // -- Handlers --------------------------------------------------------------
  const handleBack = React.useCallback(() => {
    router.push(`/${workspaceSlug}/issues`);
  }, [router, workspaceSlug]);

  // -- UI state ---------------------------------------------------------------
  const [activeTab, setActiveTab] = React.useState('description');
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [mobilePropertiesOpen, setMobilePropertiesOpen] = React.useState(false);

  const handleDeleteClick = React.useCallback(() => {
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = React.useCallback(async () => {
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

  const handleCopyLink = React.useCallback(() => {
    void copyToClipboard(window.location.href);
  }, []);

  const handleUpdate = React.useCallback(
    (data: UpdateIssueData) => updateIssue.mutateAsync(data),
    [updateIssue]
  );

  // -- Render states ---------------------------------------------------------
  if (isLoading) return <IssueDetailSkeleton />;
  if (isError || !issue) return <IssueNotFound onBack={handleBack} />;

  return (
    <div className="flex h-full flex-col">
      <IssueHeader
        identifier={issue.identifier}
        aiGenerated={issue.aiGenerated ?? false}
        showAIContext={false}
        onBack={handleBack}
        onCopyLink={handleCopyLink}
        onDelete={handleDeleteClick}
      />

      {/* T044: Responsive layout - xl: 70/30, lg: 65/35, md: stacked */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* Desktop sidebar (hidden on mobile) */}
        <div
          className="hidden shrink-0 overflow-y-auto md:block md:w-[35%] md:border-l xl:w-[30%]"
          role="complementary"
          aria-label="Issue properties"
        >
          <IssuePropertiesPanel
            issue={issue}
            workspaceId={workspaceId}
            workspaceSlug={workspaceSlug}
            members={members}
            labels={labels}
            cycles={cyclesData?.items ?? []}
            onUpdate={handleUpdate}
          />
        </div>

        {/* Mobile properties FAB + Sheet */}
        <div className="fixed bottom-6 right-6 z-40 md:hidden">
          <Sheet open={mobilePropertiesOpen} onOpenChange={setMobilePropertiesOpen}>
            <SheetTrigger asChild>
              <Button
                size="icon"
                className="size-12 rounded-full shadow-lg"
                aria-label="Open issue properties"
              >
                <SlidersHorizontal className="size-5" />
              </Button>
            </SheetTrigger>
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
                  cycles={cyclesData?.items ?? []}
                  onUpdate={handleUpdate}
                />
              )}
            </SheetContent>
          </Sheet>
        </div>

        {/* Main content area with tabs */}
        <main className="flex-1 overflow-hidden md:w-[65%] xl:w-[70%]">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex h-full flex-col">
            <TabsList className="shrink-0 justify-start rounded-none border-b bg-transparent px-6 pt-2 h-auto">
              <TabsTrigger
                value="description"
                className="rounded-t-lg data-[state=active]:bg-background data-[state=active]:shadow-sm"
              >
                Description
              </TabsTrigger>
              <TabsTrigger
                value="ai-context"
                className="gap-1.5 rounded-t-lg data-[state=active]:bg-ai/10 data-[state=active]:text-ai"
              >
                <Sparkles className="size-3.5" />
                AI Context
              </TabsTrigger>
            </TabsList>

            <TabsContent
              value="description"
              className="mt-0 flex-1 overflow-y-auto p-6 pb-24 md:pb-6"
            >
              <div className="max-w-3xl space-y-6">
                {/* Core: always visible */}
                <IssueTitle title={issue.name} issueId={issueId} workspaceId={workspaceId} />
                <IssueDescriptionEditor
                  content={issue.descriptionHtml ?? issue.description}
                  issueId={issueId}
                  workspaceId={workspaceId}
                />

                {/* AI Tasks summary (surfaced from AI Context) */}
                <TaskProgressWidget
                  issueId={issueId}
                  onViewAll={() => setActiveTab('ai-context')}
                />

                {/* Specification: collapsed when empty */}
                <CollapsibleSection
                  title="Specification"
                  icon={<ClipboardList className="size-4" />}
                  defaultOpen={
                    (issue.acceptanceCriteria?.length ?? 0) > 0 || !!issue.technicalRequirements
                  }
                  count={
                    (issue.acceptanceCriteria?.length ?? 0) + (issue.technicalRequirements ? 1 : 0)
                  }
                >
                  <div className="space-y-4">
                    <AcceptanceCriteriaEditor
                      issueId={issueId}
                      workspaceId={workspaceId}
                      criteria={issue.acceptanceCriteria ?? []}
                    />
                    <Separator />
                    <TechnicalRequirementsEditor
                      issueId={issueId}
                      workspaceId={workspaceId}
                      value={issue.technicalRequirements ?? ''}
                    />
                  </div>
                </CollapsibleSection>

                {/* Sub-issues: always visible */}
                <SubIssuesList
                  parentId={issue.id}
                  workspaceId={workspaceId}
                  workspaceSlug={workspaceSlug}
                  projectId={issue.project?.id ?? ''}
                  subIssues={[]}
                />

                {/* Activity: collapsible, default open */}
                <CollapsibleSection
                  title="Activity"
                  icon={<MessageSquare className="size-4" />}
                  defaultOpen={true}
                >
                  <ActivityTimeline issueId={issueId} workspaceId={workspaceId} />
                </CollapsibleSection>
              </div>
            </TabsContent>

            <TabsContent value="ai-context" className="mt-0 flex-1 overflow-hidden">
              <AIContextTab issueId={issueId} />
            </TabsContent>
          </Tabs>
        </main>
      </div>
      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        issues={[issue]}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />
    </div>
  );
});

export default IssueDetailPage;
