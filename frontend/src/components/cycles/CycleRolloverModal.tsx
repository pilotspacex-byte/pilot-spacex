'use client';

/**
 * CycleRolloverModal - Modal for rolling over incomplete issues to another cycle.
 *
 * T168: Allows selecting incomplete issues and target cycle for rollover.
 *
 * @example
 * ```tsx
 * <CycleRolloverModal
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   sourceCycle={currentCycle}
 *   incompleteIssues={cycleStore.incompleteIssues}
 *   availableCycles={cycleStore.upcomingCycles}
 *   onRollover={handleRollover}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { ArrowRight, AlertCircle, CheckSquare, Square, Loader2, ArrowUpRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { Cycle, RolloverCycleData, RolloverCycleResult } from '@/types';
import type { CycleIssue } from '@/stores/features/cycles';

// ============================================================================
// Types
// ============================================================================

export interface CycleRolloverModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback to change open state */
  onOpenChange: (open: boolean) => void;
  /** Source cycle to rollover from */
  sourceCycle: Cycle | null;
  /** Incomplete issues in the source cycle */
  incompleteIssues: CycleIssue[];
  /** Available target cycles */
  availableCycles: Cycle[];
  /** Loading state */
  isLoading?: boolean;
  /** Callback when rollover is confirmed */
  onRollover: (data: RolloverCycleData) => Promise<RolloverCycleResult | null>;
  /** Callback when rollover completes successfully */
  onSuccess?: (result: RolloverCycleResult) => void;
}

interface IssueSelectionProps {
  issue: CycleIssue;
  isSelected: boolean;
  onToggle: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatDateRange(startDate?: string, endDate?: string): string {
  if (!startDate && !endDate) return 'No dates set';

  const formatDate = (date: string) =>
    new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });

  if (startDate && endDate) {
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
  }
  if (startDate) return `Starts ${formatDate(startDate)}`;
  return `Ends ${formatDate(endDate!)}`;
}

const priorityColors: Record<string, string> = {
  urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  none: 'bg-muted text-muted-foreground',
};

// ============================================================================
// Issue Selection Item
// ============================================================================

const IssueSelectionItem = React.memo(function IssueSelectionItem({
  issue,
  isSelected,
  onToggle,
}: IssueSelectionProps) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-3 transition-colors cursor-pointer',
        isSelected ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted/50'
      )}
      onClick={onToggle}
      role="checkbox"
      aria-checked={isSelected}
    >
      <Checkbox checked={isSelected} onCheckedChange={onToggle} className="mt-0.5" />

      <div className="flex-1 min-w-0">
        {/* Identifier and priority */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-muted-foreground">{issue.identifier}</span>
          <Badge variant="secondary" className={cn('text-xs', priorityColors[issue.priority])}>
            {issue.priority}
          </Badge>
          <Badge variant="outline" className="text-xs capitalize">
            {issue.state?.name ?? 'Backlog'}
          </Badge>
        </div>

        {/* Title */}
        <p className="text-sm font-medium line-clamp-2">{issue.title}</p>

        {/* Assignee */}
        {issue.assignee && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-muted-foreground">
            <Avatar className="size-4">
              <AvatarFallback className="text-[8px]">
                {getInitials(issue.assignee.displayName ?? issue.assignee.email)}
              </AvatarFallback>
            </Avatar>
            <span>{issue.assignee.displayName ?? issue.assignee.email}</span>
          </div>
        )}
      </div>
    </div>
  );
});

// ============================================================================
// Target Cycle Selector
// ============================================================================

interface TargetCycleSelectorProps {
  cycles: Cycle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function TargetCycleSelector({ cycles, selectedId, onSelect }: TargetCycleSelectorProps) {
  return (
    <Select value={selectedId ?? undefined} onValueChange={onSelect}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select target cycle" />
      </SelectTrigger>
      <SelectContent>
        {cycles.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No upcoming cycles available
          </div>
        ) : (
          cycles.map((cycle) => (
            <SelectItem key={cycle.id} value={cycle.id}>
              <div className="flex items-center gap-2">
                <span className="font-medium">{cycle.name}</span>
                {cycle.startDate && cycle.endDate && (
                  <span className="text-xs text-muted-foreground">
                    ({formatDateRange(cycle.startDate, cycle.endDate)})
                  </span>
                )}
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
}

// ============================================================================
// Summary Preview
// ============================================================================

interface SummaryPreviewProps {
  selectedCount: number;
  totalCount: number;
  sourceCycleName: string;
  targetCycleName: string | null;
}

function SummaryPreview({
  selectedCount,
  totalCount,
  sourceCycleName,
  targetCycleName,
}: SummaryPreviewProps) {
  return (
    <div className="rounded-lg bg-muted/50 p-4">
      <h4 className="text-sm font-medium mb-3">Rollover Summary</h4>

      <div className="flex items-center gap-3 text-sm">
        <div className="flex-1 text-center">
          <p className="text-muted-foreground">From</p>
          <p className="font-medium truncate">{sourceCycleName}</p>
        </div>

        <ArrowRight className="size-5 text-muted-foreground shrink-0" />

        <div className="flex-1 text-center">
          <p className="text-muted-foreground">To</p>
          <p className="font-medium truncate">{targetCycleName ?? 'Select cycle'}</p>
        </div>
      </div>

      <Separator className="my-3" />

      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Issues to rollover:</span>
        <span className="font-medium">
          {selectedCount} of {totalCount}
        </span>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const CycleRolloverModal = observer(function CycleRolloverModal({
  open,
  onOpenChange,
  sourceCycle,
  incompleteIssues,
  availableCycles,
  isLoading = false,
  onRollover,
  onSuccess,
}: CycleRolloverModalProps) {
  // State
  const [selectedIssueIds, setSelectedIssueIds] = React.useState<Set<string>>(new Set());
  const [targetCycleId, setTargetCycleId] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [completeSourceCycle, setCompleteSourceCycle] = React.useState(true);

  // Reset state when modal opens
  React.useEffect(() => {
    if (open) {
      setSelectedIssueIds(new Set(incompleteIssues.map((i) => i.id)));
      setTargetCycleId(null);
      setIsSubmitting(false);
      setCompleteSourceCycle(true);
    }
  }, [open, incompleteIssues]);

  // Handlers
  const handleToggleIssue = (issueId: string) => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      if (next.has(issueId)) {
        next.delete(issueId);
      } else {
        next.add(issueId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIssueIds.size === incompleteIssues.length) {
      setSelectedIssueIds(new Set());
    } else {
      setSelectedIssueIds(new Set(incompleteIssues.map((i) => i.id)));
    }
  };

  const handleRollover = async () => {
    if (!targetCycleId || selectedIssueIds.size === 0) return;

    setIsSubmitting(true);

    try {
      const result = await onRollover({
        targetCycleId,
        issueIds: Array.from(selectedIssueIds),
        includeInProgress: true,
        completeSourceCycle,
      });

      if (result) {
        onSuccess?.(result);
        onOpenChange(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Derived state
  const targetCycle = availableCycles.find((c) => c.id === targetCycleId);
  const canSubmit = targetCycleId && selectedIssueIds.size > 0 && !isSubmitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowUpRight className="size-5" />
            Rollover Issues
          </DialogTitle>
          <DialogDescription>
            Move incomplete issues from {sourceCycle?.name ?? 'this cycle'} to another cycle.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-4">
          {/* Target cycle selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Target Cycle</label>
            <TargetCycleSelector
              cycles={availableCycles}
              selectedId={targetCycleId}
              onSelect={setTargetCycleId}
            />
            {availableCycles.length === 0 && (
              <p className="text-sm text-amber-600 flex items-center gap-1">
                <AlertCircle className="size-4" />
                Create a new cycle first to rollover issues
              </p>
            )}
          </div>

          {/* Issue selection */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">
                Issues to Rollover ({selectedIssueIds.size})
              </label>
              <Button variant="ghost" size="sm" onClick={handleSelectAll}>
                {selectedIssueIds.size === incompleteIssues.length ? (
                  <>
                    <Square className="size-4 mr-1" />
                    Deselect All
                  </>
                ) : (
                  <>
                    <CheckSquare className="size-4 mr-1" />
                    Select All
                  </>
                )}
              </Button>
            </div>

            <ScrollArea className="flex-1 border rounded-lg">
              <div className="p-2 space-y-2">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="size-6 animate-spin text-muted-foreground" />
                  </div>
                ) : incompleteIssues.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <CheckSquare className="size-12 text-green-500/50 mb-2" />
                    <p className="text-muted-foreground">No incomplete issues in this cycle</p>
                  </div>
                ) : (
                  incompleteIssues.map((issue) => (
                    <IssueSelectionItem
                      key={issue.id}
                      issue={issue}
                      isSelected={selectedIssueIds.has(issue.id)}
                      onToggle={() => handleToggleIssue(issue.id)}
                    />
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Options */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="complete-source"
              checked={completeSourceCycle}
              onCheckedChange={(checked) => setCompleteSourceCycle(checked === true)}
            />
            <label
              htmlFor="complete-source"
              className="text-sm text-muted-foreground cursor-pointer"
            >
              Mark {sourceCycle?.name ?? 'source cycle'} as completed after rollover
            </label>
          </div>

          {/* Summary */}
          <SummaryPreview
            selectedCount={selectedIssueIds.size}
            totalCount={incompleteIssues.length}
            sourceCycleName={sourceCycle?.name ?? 'Current Cycle'}
            targetCycleName={targetCycle?.name ?? null}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <TooltipProvider>
            <UITooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button onClick={handleRollover} disabled={!canSubmit} className="gap-2">
                    {isSubmitting ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Rolling over...
                      </>
                    ) : (
                      <>
                        <ArrowUpRight className="size-4" />
                        Rollover {selectedIssueIds.size} Issues
                      </>
                    )}
                  </Button>
                </span>
              </TooltipTrigger>
              {!canSubmit && (
                <TooltipContent>
                  {!targetCycleId
                    ? 'Select a target cycle'
                    : selectedIssueIds.size === 0
                      ? 'Select at least one issue'
                      : 'Processing...'}
                </TooltipContent>
              )}
            </UITooltip>
          </TooltipProvider>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

// Tooltip alias for use in this file
const UITooltip = Tooltip;

export default CycleRolloverModal;
