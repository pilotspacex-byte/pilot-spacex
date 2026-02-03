'use client';

/**
 * CycleDetailPage - Single cycle view with board, metrics, and actions.
 *
 * T171: Displays cycle board, burndown/velocity charts, and cycle actions.
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Play,
  Check,
  ArrowUpRight,
  Calendar,
  Users,
  Target,
  BarChart3,
  LayoutGrid,
  List,
  Settings,
  MoreHorizontal,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useStore } from '@/stores';
import { CycleBoard, VelocityChart, BurndownChart, CycleRolloverModal } from '@/components/cycles';
import {
  useCycle,
  useCycleIssues,
  useCycleBurndown,
  useVelocity,
  useActivateCycle,
  useCompleteCycle,
  useRolloverCycle,
  useCycles,
  selectAllCycles,
} from '@/features/cycles/hooks';
import type { Issue, IssueState, RolloverCycleData } from '@/types';
import type { CycleIssue } from '@/stores/features/cycles';
import { stateNameToKey } from '@/lib/issue-helpers';

// ============================================================================
// Types
// ============================================================================

type TabValue = 'board' | 'metrics' | 'issues';

// ============================================================================
// Helper Functions
// ============================================================================

function formatDateRange(startDate?: string, endDate?: string): string {
  if (!startDate && !endDate) return 'No dates set';

  const formatDate = (date: string) =>
    new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

  if (startDate && endDate) {
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
  }
  if (startDate) return `Starts ${formatDate(startDate)}`;
  return `Ends ${formatDate(endDate!)}`;
}

function getStatusBadgeVariant(
  status: string
): 'default' | 'secondary' | 'outline' | 'destructive' {
  switch (status) {
    case 'active':
      return 'default';
    case 'completed':
      return 'secondary';
    case 'cancelled':
      return 'destructive';
    default:
      return 'outline';
  }
}

function groupIssuesByState(issues: Issue[]): Record<IssueState, CycleIssue[]> {
  const states: IssueState[] = ['backlog', 'todo', 'in_progress', 'in_review', 'done', 'cancelled'];
  const grouped: Record<IssueState, CycleIssue[]> = {} as Record<IssueState, CycleIssue[]>;

  states.forEach((state) => {
    grouped[state] = issues.filter((i) => stateNameToKey(i.state.name) === state) as CycleIssue[];
  });

  return grouped;
}

// ============================================================================
// Stats Card Component
// ============================================================================

interface StatsCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  description?: string;
}

function StatsCard({ label, value, icon: Icon, description }: StatsCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-4">
          <div className="rounded-full bg-primary/10 p-3">
            <Icon className="size-5 text-primary" />
          </div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
            {description && <p className="text-xs text-muted-foreground/70 mt-1">{description}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function CycleDetailSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div>
            <Skeleton className="h-6 w-48 mb-2" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      <div className="flex-1 p-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-[500px]" />
      </div>
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

const CycleDetailPage = observer(function CycleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const projectId = params.projectId as string;
  const cycleId = params.cycleId as string;

  const { workspaceStore, issueStore } = useStore();
  const workspace = workspaceStore.currentWorkspace;
  const workspaceId = workspace?.id ?? '';

  // State
  const [activeTab, setActiveTab] = React.useState<TabValue>('board');
  const [isRolloverModalOpen, setIsRolloverModalOpen] = React.useState(false);
  const [showSwimlanes, setShowSwimlanes] = React.useState(false);

  // Queries
  const {
    data: cycle,
    isLoading: isLoadingCycle,
    error,
  } = useCycle({
    workspaceId,
    cycleId,
    includeMetrics: true,
    enabled: !!workspaceId && !!cycleId,
  });

  const { data: issuesData, isLoading: isLoadingIssues } = useCycleIssues({
    workspaceId,
    cycleId,
    enabled: !!workspaceId && !!cycleId,
  });

  const { data: burndownData, isLoading: isLoadingBurndown } = useCycleBurndown({
    workspaceId,
    cycleId,
    enabled: !!workspaceId && !!cycleId && activeTab === 'metrics',
  });

  const { data: velocityData, isLoading: isLoadingVelocity } = useVelocity({
    workspaceId,
    projectId,
    enabled: !!workspaceId && !!projectId && activeTab === 'metrics',
  });

  const { data: cyclesData } = useCycles({
    workspaceId,
    projectId,
    enabled: !!workspaceId && !!projectId && isRolloverModalOpen,
  });

  // Mutations
  const activateCycleMutation = useActivateCycle({
    workspaceId,
    projectId,
  });

  const completeCycleMutation = useCompleteCycle({
    workspaceId,
    projectId,
  });

  const rolloverMutation = useRolloverCycle({
    workspaceId,
    projectId,
    sourceCycleId: cycleId,
    onSuccess: () => {
      setIsRolloverModalOpen(false);
    },
  });

  // Derived data
  const issues = issuesData?.items ?? [];
  const issuesByState = groupIssuesByState(issues);
  const incompleteIssues = issues.filter(
    (i) => i.state.group !== 'completed' && i.state.group !== 'cancelled'
  ) as CycleIssue[];

  // Available target cycles for rollover (exclude current cycle)
  const availableCycles = selectAllCycles(cyclesData).filter(
    (c) => c.id !== cycleId && (c.status === 'draft' || c.status === 'active')
  );

  const metrics = cycle?.metrics;

  // Handlers
  const handleBack = () => {
    router.push(`/${workspaceSlug}/projects/${projectId}/cycles`);
  };

  const handleIssueClick = (issue: Issue) => {
    router.push(`/${workspaceSlug}/issues/${issue.id}`);
  };

  const handleIssueDrop = async (issueId: string, newState: IssueState) => {
    if (!workspaceId) return;
    await issueStore.updateIssueState(workspaceId, issueId, newState);
  };

  const handleActivate = () => {
    activateCycleMutation.mutate(cycleId);
  };

  const handleComplete = () => {
    completeCycleMutation.mutate(cycleId);
  };

  const handleRollover = async (data: RolloverCycleData) => {
    return rolloverMutation.mutateAsync(data);
  };

  // Loading state
  if (isLoadingCycle) {
    return <CycleDetailSkeleton />;
  }

  // Error state
  if (error || !cycle) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16">
        <AlertCircle className="size-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Failed to load cycle</h2>
        <p className="text-muted-foreground mb-4">{error?.message ?? 'Cycle not found'}</p>
        <Button onClick={handleBack}>
          <ArrowLeft className="size-4 mr-2" />
          Back to Cycles
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="size-5" />
          </Button>

          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-semibold">{cycle.name}</h1>
              <Badge variant={getStatusBadgeVariant(cycle.status)}>
                {cycle.status.charAt(0).toUpperCase() + cycle.status.slice(1)}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="size-4" />
                {formatDateRange(cycle.startDate, cycle.endDate)}
              </span>
              <span className="flex items-center gap-1">
                <Target className="size-4" />
                {cycle.issueCount} issues
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {cycle.status === 'draft' && (
            <Button onClick={handleActivate}>
              <Play className="size-4 mr-2" />
              Start Cycle
            </Button>
          )}

          {cycle.status === 'active' && (
            <>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      onClick={() => setIsRolloverModalOpen(true)}
                      disabled={incompleteIssues.length === 0}
                    >
                      <ArrowUpRight className="size-4 mr-2" />
                      Rollover
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {incompleteIssues.length === 0
                      ? 'No incomplete issues to rollover'
                      : `Rollover ${incompleteIssues.length} incomplete issues`}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <Button onClick={handleComplete}>
                <Check className="size-4 mr-2" />
                Complete
              </Button>
            </>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Settings className="size-4 mr-2" />
                Edit Cycle
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">Delete Cycle</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-6 py-4 border-b bg-muted/30">
          <StatsCard label="Total Issues" value={metrics.totalIssues} icon={Target} />
          <StatsCard
            label="Completed"
            value={metrics.completedIssues}
            icon={Check}
            description={`${metrics.completionPercentage}% complete`}
          />
          <StatsCard label="In Progress" value={metrics.inProgressIssues} icon={Play} />
          <StatsCard
            label="Velocity"
            value={metrics.velocity.toFixed(1)}
            icon={BarChart3}
            description="points/cycle"
          />
        </div>
      )}

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as TabValue)}
        className="flex-1 flex flex-col"
      >
        <div className="flex items-center justify-between border-b px-6 py-2">
          <TabsList>
            <TabsTrigger value="board" className="gap-2">
              <LayoutGrid className="size-4" />
              Board
            </TabsTrigger>
            <TabsTrigger value="metrics" className="gap-2">
              <BarChart3 className="size-4" />
              Metrics
            </TabsTrigger>
            <TabsTrigger value="issues" className="gap-2">
              <List className="size-4" />
              Issues
            </TabsTrigger>
          </TabsList>

          {activeTab === 'board' && (
            <div className="flex items-center gap-2">
              <Button
                variant={showSwimlanes ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setShowSwimlanes(!showSwimlanes)}
              >
                <Users className="size-4 mr-2" />
                Swimlanes
              </Button>
            </div>
          )}
        </div>

        {/* Board Tab */}
        <TabsContent value="board" className="flex-1 m-0">
          <CycleBoard
            issuesByState={issuesByState}
            onIssueClick={handleIssueClick}
            onIssueDrop={handleIssueDrop}
            isLoading={isLoadingIssues}
            showSwimlanes={showSwimlanes}
            excludeColumns={['cancelled']}
          />
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics" className="flex-1 m-0 overflow-auto">
          <div className="p-6 space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BurndownChart
                data={burndownData ?? null}
                isLoading={isLoadingBurndown}
                height={350}
              />
              <VelocityChart
                data={velocityData ?? null}
                isLoading={isLoadingVelocity}
                height={350}
              />
            </div>

            {/* Additional stats */}
            {metrics && (
              <Card>
                <CardHeader>
                  <CardTitle>Cycle Statistics</CardTitle>
                  <CardDescription>Detailed metrics for this cycle</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Points</p>
                      <p className="text-2xl font-bold">{metrics.totalPoints}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Completed Points</p>
                      <p className="text-2xl font-bold">{metrics.completedPoints}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Not Started</p>
                      <p className="text-2xl font-bold">{metrics.notStartedIssues}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Completion Rate</p>
                      <p className="text-2xl font-bold">{metrics.completionPercentage}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Issues Tab */}
        <TabsContent value="issues" className="flex-1 m-0 overflow-auto">
          <div className="p-6">
            <Card>
              <CardHeader>
                <CardTitle>Issues ({issues.length})</CardTitle>
                <CardDescription>All issues assigned to this cycle</CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingIssues ? (
                  <div className="space-y-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-16" />
                    ))}
                  </div>
                ) : issues.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No issues in this cycle
                  </div>
                ) : (
                  <div className="space-y-2">
                    {issues.map((issue) => (
                      <div
                        key={issue.id}
                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 cursor-pointer"
                        onClick={() => handleIssueClick(issue)}
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-mono text-muted-foreground">
                            {issue.identifier}
                          </span>
                          <span className="font-medium">{issue.title}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="capitalize">
                            {issue.state.name}
                          </Badge>
                          <Badge variant="secondary" className="capitalize">
                            {issue.priority}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Rollover Modal */}
      <CycleRolloverModal
        open={isRolloverModalOpen}
        onOpenChange={setIsRolloverModalOpen}
        sourceCycle={cycle}
        incompleteIssues={incompleteIssues}
        availableCycles={availableCycles}
        isLoading={isLoadingIssues}
        onRollover={handleRollover}
      />
    </div>
  );
});

export default CycleDetailPage;
