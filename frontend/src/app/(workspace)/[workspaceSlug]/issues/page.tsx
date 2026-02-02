'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import { LayoutGrid, List, Table, Plus, Search, Filter, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { IssueBoard, IssueModal } from '@/components/issues';
import { useStore } from '@/stores';
import type { Issue, IssueState, Label, User, CreateIssueData, UpdateIssueData } from '@/types';

/**
 * IssuesPage displays the main issues view with board/list/table modes.
 * Integrates with IssueStore for state management.
 */
const IssuesPage = observer(function IssuesPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;

  const { issueStore, workspaceStore } = useStore();

  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [selectedIssue, setSelectedIssue] = React.useState<Issue | null>(null);
  const [defaultState, setDefaultState] = React.useState<IssueState>('backlog');

  // Get current workspace - fallback to slug if store hasn't loaded workspace yet
  const workspace = workspaceStore.currentWorkspace;
  const workspaceId = workspace?.id ?? workspaceSlug;
  // Project ID for filtering (null means all projects)
  const projectId: string | undefined = undefined;

  // Load issues on mount
  React.useEffect(() => {
    if (workspaceId) {
      issueStore.loadIssues(workspaceId, projectId);
    }
  }, [workspaceId, projectId, issueStore]);

  // Handlers
  const handleCreateIssue = (state?: IssueState) => {
    setSelectedIssue(null);
    setDefaultState(state ?? 'backlog');
    setIsModalOpen(true);
  };

  const handleEditIssue = (issue: Issue) => {
    setSelectedIssue(issue);
    setIsModalOpen(true);
  };

  const handleIssueDrop = async (issueId: string, newState: IssueState) => {
    if (workspaceId) {
      await issueStore.updateIssueState(workspaceId, issueId, newState);
    }
  };

  const handleSaveIssue = async (
    data: CreateIssueData | UpdateIssueData
  ): Promise<Issue | null> => {
    if (!workspaceId) return null;

    if (selectedIssue) {
      return issueStore.updateIssue(workspaceId, selectedIssue.id, data);
    }
    // For create, ensure required fields are present
    const createData = data as CreateIssueData;
    return issueStore.createIssue(workspaceId, createData);
  };

  const handleViewModeChange = (mode: 'board' | 'list' | 'table') => {
    issueStore.setViewMode(mode);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    issueStore.setSearchQuery(e.target.value);
  };

  const handleFilterChange = (key: string, value: string) => {
    if (value === 'all') {
      issueStore.setFilters({ [key]: undefined });
    } else {
      issueStore.setFilters({ [key]: value });
    }
  };

  // Mock data for labels and members (in real app, these come from stores)
  const availableLabels: Label[] = [];
  const teamMembers: User[] = [];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h1 className="text-2xl font-semibold">Issues</h1>
          <p className="text-sm text-muted-foreground">
            {projectId ? 'Project issues' : 'All projects'}
          </p>
        </div>

        <Button onClick={() => handleCreateIssue()}>
          <Plus className="mr-2 size-4" />
          New Issue
        </Button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-4 border-b px-6 py-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search issues..."
            value={issueStore.searchQuery}
            onChange={handleSearchChange}
            className="pl-9"
          />
        </div>

        {/* Filters */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="mr-2 size-4" />
              Filter
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuLabel>Filter by</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="p-2 space-y-2">
              <div className="space-y-1">
                <label className="text-xs font-medium">State</label>
                <Select
                  value={issueStore.filters.state ?? 'all'}
                  onValueChange={(v) => handleFilterChange('state', v)}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="All states" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All states</SelectItem>
                    <SelectItem value="backlog">Backlog</SelectItem>
                    <SelectItem value="todo">Todo</SelectItem>
                    <SelectItem value="in_progress">In Progress</SelectItem>
                    <SelectItem value="in_review">In Review</SelectItem>
                    <SelectItem value="done">Done</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Priority</label>
                <Select
                  value={issueStore.filters.priority ?? 'all'}
                  onValueChange={(v) => handleFilterChange('priority', v)}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="All priorities" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All priorities</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="none">No priority</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Sort */}
        <Select
          value={issueStore.sortBy}
          onValueChange={(v) =>
            issueStore.setSortBy(v as 'created' | 'updated' | 'priority' | 'title')
          }
        >
          <SelectTrigger className="w-32">
            <SlidersHorizontal className="mr-2 size-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="updated">Updated</SelectItem>
            <SelectItem value="created">Created</SelectItem>
            <SelectItem value="priority">Priority</SelectItem>
            <SelectItem value="title">Title</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex-1" />

        {/* View mode toggle */}
        <div className="flex items-center rounded-md border">
          <Button
            variant={issueStore.viewMode === 'board' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => handleViewModeChange('board')}
            className="rounded-r-none"
          >
            <LayoutGrid className="size-4" />
          </Button>
          <Button
            variant={issueStore.viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => handleViewModeChange('list')}
            className="rounded-none border-x"
          >
            <List className="size-4" />
          </Button>
          <Button
            variant={issueStore.viewMode === 'table' ? 'secondary' : 'ghost'}
            size="icon-sm"
            onClick={() => handleViewModeChange('table')}
            className="rounded-l-none"
          >
            <Table className="size-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {issueStore.viewMode === 'board' && (
          <IssueBoard
            issuesByState={issueStore.issuesByState}
            onIssueClick={handleEditIssue}
            onOpenIssue={(issue) => router.push(`/${workspaceSlug}/issues/${issue.id}`)}
            onIssueDrop={handleIssueDrop}
            onCreateIssue={handleCreateIssue}
            isLoading={issueStore.isLoading}
          />
        )}

        {issueStore.viewMode === 'list' && (
          <div className="p-6">
            <p className="text-muted-foreground">List view coming soon...</p>
          </div>
        )}

        {issueStore.viewMode === 'table' && (
          <div className="p-6">
            <p className="text-muted-foreground">Table view coming soon...</p>
          </div>
        )}
      </div>

      {/* Issue Modal */}
      <IssueModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        issue={selectedIssue}
        defaultState={defaultState}
        availableLabels={availableLabels}
        teamMembers={teamMembers}
        projectId={projectId ?? ''}
        enhancementSuggestion={issueStore.enhancementSuggestion}
        duplicateResult={issueStore.duplicateCheckResult}
        assigneeRecommendations={issueStore.assigneeRecommendations}
        isLoadingEnhancement={issueStore.isLoadingEnhancement}
        isCheckingDuplicates={issueStore.isCheckingDuplicates}
        onRequestEnhancement={(title, desc) => {
          if (workspace?.id && projectId) {
            issueStore.getEnhancementSuggestions(workspace.id, title, desc, projectId);
          }
        }}
        onCheckDuplicates={(title, desc) => {
          if (workspace?.id) {
            issueStore.checkForDuplicates(workspace.id, title, desc, projectId);
          }
        }}
        onRequestAssigneeRecommendations={(labelNames) => {
          if (workspace?.id && projectId) {
            issueStore.getAssigneeRecommendations(
              workspace.id,
              selectedIssue?.title ?? '',
              selectedIssue?.description ?? null,
              labelNames,
              projectId
            );
          }
        }}
        onSave={handleSaveIssue}
        onOpenIssue={(issue) => {
          router.push(`/${workspaceSlug}/issues/${issue.id}`);
        }}
        onViewDuplicate={(issueId) => {
          router.push(`/${workspaceSlug}/issues/${issueId}`);
        }}
        onRecordDecision={(type, accepted) => {
          if (workspace?.id && selectedIssue?.id) {
            issueStore.recordSuggestionDecision(workspace.id, selectedIssue.id, type, accepted);
          }
        }}
      />
    </div>
  );
});

export default IssuesPage;
