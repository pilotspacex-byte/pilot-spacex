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
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  IssueHeader,
  AIContextSidebar,
  IssueTitle,
  IssueDescriptionEditor,
  SubIssuesList,
  ActivityTimeline,
  IssuePropertiesPanel,
} from '@/features/issues/components';
import {
  useIssueDetail,
  useUpdateIssue,
  useWorkspaceMembers,
  useWorkspaceLabels,
  useProjectCycles,
  useIssueKeyboardShortcuts,
} from '@/features/issues/hooks';
import { useStore } from '@/stores';
import type { UpdateIssueData } from '@/types';

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

  const { workspaceStore, aiStore, issueStore } = useStore();
  // Backend accepts both UUID and slug — use slug as fallback when store isn't hydrated
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  // -- TanStack Query hooks --------------------------------------------------
  const { data: issue, isLoading, isError } = useIssueDetail(workspaceId, issueId);
  const updateIssue = useUpdateIssue(workspaceId, issueId);
  const { data: members = [] } = useWorkspaceMembers(workspaceId);
  const { data: labels = [] } = useWorkspaceLabels(workspaceId);
  const { data: cyclesData } = useProjectCycles(workspaceId, issue?.project?.id ?? '');

  // -- UI state (MobX-appropriate) -------------------------------------------
  const [isAIContextOpen, setIsAIContextOpen] = React.useState(false);

  // -- Keyboard shortcuts (T045) ---------------------------------------------
  const handleForceSave = React.useCallback(() => {
    document.dispatchEvent(new CustomEvent('issue-force-save'));
  }, []);

  useIssueKeyboardShortcuts({
    onCloseAISidebar: () => setIsAIContextOpen(false),
    onForceSave: handleForceSave,
  });

  // -- Handlers --------------------------------------------------------------
  const handleBack = React.useCallback(() => {
    router.push(`/${workspaceSlug}/issues`);
  }, [router, workspaceSlug]);

  const handleDelete = React.useCallback(async () => {
    if (!workspaceId || !issue?.id) return;
    const confirmed = window.confirm('Are you sure you want to delete this issue?');
    if (!confirmed) return;
    await issueStore.deleteIssue(workspaceId, issue.id);
    router.push(`/${workspaceSlug}/issues`);
  }, [workspaceId, issue?.id, issueStore, router, workspaceSlug]);

  const handleCopyLink = React.useCallback(() => {
    void navigator.clipboard.writeText(window.location.href);
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
        showAIContext={aiStore.settings.aiContextEnabled}
        onBack={handleBack}
        onAIContextClick={() => setIsAIContextOpen(true)}
        onCopyLink={handleCopyLink}
        onDelete={handleDelete}
      />

      {/* T044: Responsive layout - xl: 70/30, lg: 65/35, md: stacked */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* Properties sidebar - shown first on mobile, right on desktop */}
        <div
          className="order-first shrink-0 overflow-y-auto border-b md:order-last md:w-[35%] md:border-b-0 md:border-l lg:w-[35%] xl:w-[30%]"
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

        {/* Main content area */}
        <main className="flex-1 overflow-y-auto p-6 md:w-[65%] lg:w-[65%] xl:w-[70%]">
          <div className="max-w-3xl space-y-6">
            <IssueTitle title={issue.name} issueId={issueId} workspaceId={workspaceId} />

            <IssueDescriptionEditor
              content={issue.descriptionHtml}
              issueId={issueId}
              workspaceId={workspaceId}
            />

            <Separator />

            <SubIssuesList
              parentId={issue.id}
              workspaceId={workspaceId}
              workspaceSlug={workspaceSlug}
              projectId={issue.project?.id ?? ''}
              subIssues={[]}
            />
            <Separator />

            <ActivityTimeline issueId={issueId} workspaceId={workspaceId} />
          </div>
        </main>
      </div>

      <AIContextSidebar
        issueId={issueId}
        issueIdentifier={issue.identifier}
        open={isAIContextOpen}
        onOpenChange={setIsAIContextOpen}
      />
    </div>
  );
});

export default IssueDetailPage;
