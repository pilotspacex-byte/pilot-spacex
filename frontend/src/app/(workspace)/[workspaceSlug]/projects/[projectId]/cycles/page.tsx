'use client';

/**
 * CyclesPage - List all cycles for a project.
 *
 * T170: Displays active, upcoming, and past cycles with quick stats.
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import {
  Plus,
  Play,
  Calendar,
  Target,
  MoreHorizontal,
  Check,
  Archive,
  Pencil,
  Trash2,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/stores';
import {
  useCycles,
  useCreateCycle,
  useActivateCycle,
  useCompleteCycle,
  useDeleteCycle,
  selectAllCycles,
  selectActiveCycle,
} from '@/features/cycles/hooks';
import type { Cycle, CycleStatus, CreateCycleData } from '@/types';

// ============================================================================
// Types
// ============================================================================

interface CycleCardProps {
  cycle: Cycle;
  isActive?: boolean;
  onView: () => void;
  onActivate?: () => void;
  onComplete?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatDateRange(startDate?: string, endDate?: string): string {
  if (!startDate && !endDate) return 'No dates set';

  const formatShort = (date: string) =>
    new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });

  if (startDate && endDate) {
    return `${formatShort(startDate)} - ${formatShort(endDate)}`;
  }
  if (startDate) return `Starts ${formatShort(startDate)}`;
  return `Ends ${formatShort(endDate!)}`;
}

function getStatusBadgeVariant(
  status: CycleStatus
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

function getStatusLabel(status: CycleStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

// ============================================================================
// Cycle Card Component
// ============================================================================

const CycleCard = React.memo(function CycleCard({
  cycle,
  isActive = false,
  onView,
  onActivate,
  onComplete,
  onEdit,
  onDelete,
}: CycleCardProps) {
  const metrics = cycle.metrics;
  const completionPercentage = metrics?.completionPercentage ?? 0;

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all hover:shadow-md',
        isActive && 'ring-2 ring-primary'
      )}
      onClick={onView}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={getStatusBadgeVariant(cycle.status)}>
                {getStatusLabel(cycle.status)}
              </Badge>
              {isActive && (
                <Badge variant="outline" className="text-green-600 border-green-300 bg-green-50">
                  Current
                </Badge>
              )}
            </div>
            <CardTitle className="text-lg truncate">{cycle.name}</CardTitle>
            {cycle.description && (
              <CardDescription className="line-clamp-2 mt-1">{cycle.description}</CardDescription>
            )}
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="shrink-0">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {cycle.status === 'draft' && onActivate && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onActivate();
                  }}
                >
                  <Play className="size-4 mr-2" />
                  Start Cycle
                </DropdownMenuItem>
              )}
              {cycle.status === 'active' && onComplete && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onComplete();
                  }}
                >
                  <Check className="size-4 mr-2" />
                  Complete Cycle
                </DropdownMenuItem>
              )}
              {onEdit && (
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit();
                  }}
                >
                  <Pencil className="size-4 mr-2" />
                  Edit
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {onDelete && (
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete();
                  }}
                >
                  <Trash2 className="size-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Date range */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="size-4" />
          <span>{formatDateRange(cycle.startDate, cycle.endDate)}</span>
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{completionPercentage}%</span>
          </div>
          {completionPercentage > 0 ? (
            <Progress value={completionPercentage} className="h-2" />
          ) : (
            <p className="text-sm text-muted-foreground">0%</p>
          )}
        </div>

        {/* Metrics */}
        {metrics && (
          <div className="grid grid-cols-3 gap-4 pt-2 border-t">
            <div className="text-center">
              <p className="text-2xl font-bold">{metrics.completedIssues}</p>
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{metrics.inProgressIssues}</p>
              <p className="text-xs text-muted-foreground">In Progress</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{metrics.notStartedIssues}</p>
              <p className="text-xs text-muted-foreground">Not Started</p>
            </div>
          </div>
        )}

        {/* Issue count if no metrics */}
        {!metrics && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2 border-t">
            <Target className="size-4" />
            <span>{cycle.issueCount} issues</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

// ============================================================================
// Loading Skeleton
// ============================================================================

function CycleCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-20 mb-2" />
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-full mt-1" />
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-4 w-1/2" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-2 w-full" />
        </div>
        <div className="grid grid-cols-3 gap-4 pt-2 border-t">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Create Cycle Modal
// ============================================================================

interface CreateCycleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: CreateCycleData) => void;
  isLoading?: boolean;
  projectId: string;
}

function CreateCycleModal({
  open,
  onOpenChange,
  onSubmit,
  isLoading,
  projectId,
}: CreateCycleModalProps) {
  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [startDate, setStartDate] = React.useState('');
  const [endDate, setEndDate] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      projectId,
      startDate: startDate || undefined,
      endDate: endDate || undefined,
    });
  };

  // Reset form when modal closes
  React.useEffect(() => {
    if (!open) {
      setName('');
      setDescription('');
      setStartDate('');
      setEndDate('');
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Cycle</DialogTitle>
            <DialogDescription>
              Create a new sprint cycle to organize and track work.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Name <span className="text-destructive">*</span>
              </label>
              <Input
                id="name"
                placeholder="Sprint 1"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="description" className="text-sm font-medium">
                Description
              </label>
              <Textarea
                id="description"
                placeholder="Optional description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label htmlFor="startDate" className="text-sm font-medium">
                  Start Date
                </label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="endDate" className="text-sm font-medium">
                  End Date
                </label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  min={startDate}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="size-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Cycle'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

const CyclesPage = observer(function CyclesPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const projectId = params.projectId as string;

  const { workspaceStore } = useStore();
  const workspace = workspaceStore.currentWorkspace;
  const workspaceId = workspace?.id ?? '';

  // State
  const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);

  // Queries
  const {
    data: cyclesData,
    isLoading,
    error,
  } = useCycles({
    workspaceId,
    projectId,
    includeMetrics: true,
    enabled: !!workspaceId && !!projectId,
  });

  // Mutations
  const createCycleMutation = useCreateCycle({
    workspaceId,
    projectId,
    onSuccess: () => {
      setIsCreateModalOpen(false);
    },
  });

  const activateCycleMutation = useActivateCycle({
    workspaceId,
    projectId,
  });

  const completeCycleMutation = useCompleteCycle({
    workspaceId,
    projectId,
  });

  const deleteCycleMutation = useDeleteCycle({
    workspaceId,
    projectId,
  });

  // Derived data
  const allCycles = selectAllCycles(cyclesData);
  const activeCycle = selectActiveCycle(cyclesData);
  const upcomingCycles = allCycles.filter((c) => c.status === 'draft' || c.status === 'planned');
  const pastCycles = allCycles.filter((c) => c.status === 'completed' || c.status === 'cancelled');

  // Handlers
  const handleViewCycle = (cycleId: string) => {
    router.push(`/${workspaceSlug}/projects/${projectId}/cycles/${cycleId}`);
  };

  const handleCreateCycle = (data: CreateCycleData) => {
    createCycleMutation.mutate(data);
  };

  const handleActivateCycle = (cycleId: string) => {
    activateCycleMutation.mutate(cycleId);
  };

  const handleCompleteCycle = (cycleId: string) => {
    completeCycleMutation.mutate(cycleId);
  };

  const handleDeleteCycle = (cycleId: string) => {
    if (confirm('Are you sure you want to delete this cycle?')) {
      deleteCycleMutation.mutate(cycleId);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16">
        <AlertCircle className="size-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Failed to load cycles</h2>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h1 className="text-2xl font-semibold">Cycles</h1>
          <p className="text-sm text-muted-foreground">Sprint planning and tracking</p>
        </div>

        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="size-4 mr-2" />
          New Cycle
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6 space-y-8">
        {/* Active Cycle */}
        {isLoading ? (
          <section>
            <h2 className="text-lg font-semibold mb-4">Active Cycle</h2>
            <CycleCardSkeleton />
          </section>
        ) : activeCycle ? (
          <section>
            <h2 className="text-lg font-semibold mb-4">Active Cycle</h2>
            <div className="max-w-2xl">
              <CycleCard
                cycle={activeCycle}
                isActive
                onView={() => handleViewCycle(activeCycle.id)}
                onComplete={() => handleCompleteCycle(activeCycle.id)}
                onEdit={() => {}}
              />
            </div>
          </section>
        ) : (
          <section>
            <h2 className="text-lg font-semibold mb-4">Active Cycle</h2>
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Play className="size-12 text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground mb-4">
                  No active cycle. Start a cycle to begin tracking progress.
                </p>
                {upcomingCycles.length > 0 && upcomingCycles[0] ? (
                  <Button
                    variant="outline"
                    onClick={() => handleActivateCycle(upcomingCycles[0]!.id)}
                  >
                    <Play className="size-4 mr-2" />
                    Start {upcomingCycles[0]!.name}
                  </Button>
                ) : (
                  <Button onClick={() => setIsCreateModalOpen(true)}>
                    <Plus className="size-4 mr-2" />
                    Create Cycle
                  </Button>
                )}
              </CardContent>
            </Card>
          </section>
        )}

        {/* Upcoming Cycles */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Upcoming ({upcomingCycles.length})</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <CycleCardSkeleton />
              <CycleCardSkeleton />
            </div>
          ) : upcomingCycles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {upcomingCycles.map((cycle) => (
                <CycleCard
                  key={cycle.id}
                  cycle={cycle}
                  onView={() => handleViewCycle(cycle.id)}
                  onActivate={!activeCycle ? () => handleActivateCycle(cycle.id) : undefined}
                  onEdit={() => {}}
                  onDelete={() => handleDeleteCycle(cycle.id)}
                />
              ))}
            </div>
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Calendar className="size-12 text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No upcoming cycles</p>
              </CardContent>
            </Card>
          )}
        </section>

        {/* Past Cycles */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Past ({pastCycles.length})</h2>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <CycleCardSkeleton />
            </div>
          ) : pastCycles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pastCycles.map((cycle) => (
                <CycleCard
                  key={cycle.id}
                  cycle={cycle}
                  onView={() => handleViewCycle(cycle.id)}
                  onDelete={() => handleDeleteCycle(cycle.id)}
                />
              ))}
            </div>
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Archive className="size-12 text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">No past cycles</p>
              </CardContent>
            </Card>
          )}
        </section>
      </div>

      {/* Create Cycle Modal */}
      <CreateCycleModal
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
        onSubmit={handleCreateCycle}
        isLoading={createCycleMutation.isPending}
        projectId={projectId}
      />
    </div>
  );
});

export default CyclesPage;
