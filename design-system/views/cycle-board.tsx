/**
 * Cycle/Sprint Board Component
 *
 * Sprint management view with metrics and burndown visualization.
 * Follows Web Interface Guidelines:
 * - Tabular numbers for metrics
 * - Accessible progress indicators
 * - Proper date formatting with Intl.DateTimeFormat
 */

import * as React from 'react';
import { IconCalendar, IconTrendingUp, IconTrendingDown, IconClock } from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '../components/card';
import { Badge } from '../components/badge';
import { Button } from '../components/button';
import { BoardView, type BoardColumn } from './board-view';
import type { Issue, IssueState } from './issue-card';

// =============================================================================
// TYPES
// =============================================================================

export interface Cycle {
  id: string;
  name: string;
  description?: string;
  startDate: Date;
  endDate: Date;
  status: 'upcoming' | 'active' | 'completed';
  issues: Issue[];
  goals?: string[];
}

export interface CycleMetrics {
  totalIssues: number;
  completedIssues: number;
  inProgressIssues: number;
  completionPercentage: number;
  velocity: number; // Story points completed
  averageVelocity: number; // Historical average
  daysRemaining: number;
  burndownData: Array<{ date: Date; ideal: number; actual: number }>;
}

export interface CycleBoardProps {
  cycle: Cycle;
  metrics: CycleMetrics;
  onIssueMove: (issueId: string, newState: IssueState, newIndex: number) => void;
  onIssueClick: (issue: Issue) => void;
  onCreateIssue: (state: IssueState) => void;
  onEditCycle: () => void;
  onCompleteCycle: () => void;
}

// =============================================================================
// DATE FORMATTER
// =============================================================================

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

const shortDateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
});

// =============================================================================
// CYCLE HEADER
// =============================================================================

interface CycleHeaderProps {
  cycle: Cycle;
  metrics: CycleMetrics;
  onEdit: () => void;
  onComplete: () => void;
}

function CycleHeader({ cycle, metrics, onEdit, onComplete }: CycleHeaderProps) {
  const statusColors = {
    upcoming: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    completed: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  };

  return (
    <div className="mb-6 flex items-start justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-balance">{cycle.name}</h1>
          <Badge className={statusColors[cycle.status]}>
            {cycle.status.charAt(0).toUpperCase() + cycle.status.slice(1)}
          </Badge>
        </div>
        {cycle.description && (
          <p className="mt-1 text-muted-foreground">{cycle.description}</p>
        )}
        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <IconCalendar className="h-4 w-4" />
            <span>
              {shortDateFormatter.format(cycle.startDate)} -{' '}
              {shortDateFormatter.format(cycle.endDate)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <IconClock className="h-4 w-4" />
            <span className="tabular-nums">{metrics.daysRemaining} days left</span>
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onEdit}>
          Edit Cycle
        </Button>
        {cycle.status === 'active' && (
          <Button onClick={onComplete}>Complete Cycle</Button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// METRICS CARDS
// =============================================================================

interface MetricsCardsProps {
  metrics: CycleMetrics;
}

function MetricsCards({ metrics }: MetricsCardsProps) {
  const velocityTrend = metrics.velocity >= metrics.averageVelocity ? 'up' : 'down';

  return (
    <div className="mb-6 grid grid-cols-4 gap-4">
      {/* Progress */}
      <Card padding="default">
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Progress</span>
            <span className="text-2xl font-bold tabular-nums">
              {metrics.completionPercentage}%
            </span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${metrics.completionPercentage}%` }}
              role="progressbar"
              aria-valuenow={metrics.completionPercentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${metrics.completionPercentage}% complete`}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            <span className="tabular-nums">{metrics.completedIssues}</span> of{' '}
            <span className="tabular-nums">{metrics.totalIssues}</span> issues
          </p>
        </CardContent>
      </Card>

      {/* Velocity */}
      <Card padding="default">
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Velocity</span>
            <div className="flex items-center gap-1">
              {velocityTrend === 'up' ? (
                <IconTrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <IconTrendingDown className="h-4 w-4 text-red-500" />
              )}
              <span className="text-2xl font-bold tabular-nums">
                {metrics.velocity}
              </span>
            </div>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Average: <span className="tabular-nums">{metrics.averageVelocity}</span> pts
          </p>
        </CardContent>
      </Card>

      {/* In Progress */}
      <Card padding="default">
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">In Progress</span>
            <span className="text-2xl font-bold tabular-nums">
              {metrics.inProgressIssues}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Active issues</p>
        </CardContent>
      </Card>

      {/* Days Remaining */}
      <Card padding="default">
        <CardContent>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Time Left</span>
            <span
              className={cn(
                'text-2xl font-bold tabular-nums',
                metrics.daysRemaining <= 2 && 'text-destructive'
              )}
            >
              {metrics.daysRemaining}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Days remaining</p>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// BURNDOWN CHART (Simplified SVG)
// =============================================================================

interface BurndownChartProps {
  data: Array<{ date: Date; ideal: number; actual: number }>;
}

function BurndownChart({ data }: BurndownChartProps) {
  if (data.length === 0) return null;

  const maxValue = Math.max(...data.map((d) => Math.max(d.ideal, d.actual)));
  const width = 100;
  const height = 60;

  const getX = (index: number) => (index / (data.length - 1)) * width;
  const getY = (value: number) => height - (value / maxValue) * height;

  const idealPath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.ideal)}`)
    .join(' ');

  const actualPath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.actual)}`)
    .join(' ');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Burndown</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-32 w-full"
          preserveAspectRatio="none"
          role="img"
          aria-label="Sprint burndown chart showing ideal vs actual progress"
        >
          {/* Grid lines */}
          <line
            x1="0"
            y1={height}
            x2={width}
            y2={height}
            stroke="currentColor"
            strokeOpacity="0.1"
          />
          <line
            x1="0"
            y1={height / 2}
            x2={width}
            y2={height / 2}
            stroke="currentColor"
            strokeOpacity="0.1"
            strokeDasharray="2 2"
          />

          {/* Ideal line (dashed) */}
          <path
            d={idealPath}
            fill="none"
            stroke="hsl(240 5% 64.9%)"
            strokeWidth="1"
            strokeDasharray="4 2"
          />

          {/* Actual line */}
          <path
            d={actualPath}
            fill="none"
            stroke="hsl(24.6 95% 53.1%)"
            strokeWidth="2"
          />

          {/* Data points */}
          {data.map((d, i) => (
            <circle
              key={i}
              cx={getX(i)}
              cy={getY(d.actual)}
              r="2"
              fill="hsl(24.6 95% 53.1%)"
            />
          ))}
        </svg>

        <div className="mt-2 flex justify-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="h-0.5 w-4 bg-muted-foreground" style={{ strokeDasharray: '4 2' }} />
            <span>Ideal</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-0.5 w-4 bg-primary" />
            <span>Actual</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// CYCLE GOALS
// =============================================================================

interface CycleGoalsProps {
  goals: string[];
}

function CycleGoals({ goals }: CycleGoalsProps) {
  if (goals.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Sprint Goals</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {goals.map((goal, index) => (
            <li key={index} className="flex items-start gap-2">
              <div className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
              <span className="text-sm">{goal}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function CycleBoard({
  cycle,
  metrics,
  onIssueMove,
  onIssueClick,
  onCreateIssue,
  onEditCycle,
  onCompleteCycle,
}: CycleBoardProps) {
  // Group issues by state for board columns
  const columns: BoardColumn[] = React.useMemo(() => {
    const stateGroups: Record<IssueState, Issue[]> = {
      backlog: [],
      todo: [],
      'in-progress': [],
      'in-review': [],
      done: [],
      cancelled: [],
    };

    cycle.issues.forEach((issue) => {
      stateGroups[issue.state].push(issue);
    });

    return [
      { id: 'backlog', title: 'Backlog', issues: stateGroups.backlog },
      { id: 'todo', title: 'Todo', issues: stateGroups.todo },
      { id: 'in-progress', title: 'In Progress', issues: stateGroups['in-progress'] },
      { id: 'in-review', title: 'In Review', issues: stateGroups['in-review'] },
      { id: 'done', title: 'Done', issues: stateGroups.done },
    ];
  }, [cycle.issues]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <CycleHeader
        cycle={cycle}
        metrics={metrics}
        onEdit={onEditCycle}
        onComplete={onCompleteCycle}
      />

      {/* Metrics */}
      <MetricsCards metrics={metrics} />

      {/* Main content: Board + Sidebar */}
      <div className="flex gap-6">
        {/* Board */}
        <div className="min-w-0 flex-1">
          <BoardView
            columns={columns}
            onIssueMove={onIssueMove}
            onIssueClick={onIssueClick}
            onCreateIssue={onCreateIssue}
          />
        </div>

        {/* Sidebar */}
        <div className="w-80 flex-shrink-0 space-y-4">
          <BurndownChart data={metrics.burndownData} />
          {cycle.goals && <CycleGoals goals={cycle.goals} />}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// CYCLE COMPLETION MODAL
// =============================================================================

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/dialog';
import { IssueRow } from './issue-card';

export interface CycleCompleteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  cycle: Cycle;
  incompleteIssues: Issue[];
  onComplete: (action: 'rollover' | 'backlog') => void;
}

export function CycleCompleteModal({
  open,
  onOpenChange,
  cycle,
  incompleteIssues,
  onComplete,
}: CycleCompleteModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Complete "{cycle.name}"</DialogTitle>
          <DialogDescription>
            {incompleteIssues.length > 0
              ? `There are ${incompleteIssues.length} incomplete issues. What would you like to do with them?`
              : 'All issues have been completed. Ready to close this cycle?'}
          </DialogDescription>
        </DialogHeader>

        {incompleteIssues.length > 0 && (
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {incompleteIssues.map((issue) => (
              <IssueRow key={issue.id} issue={issue} />
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {incompleteIssues.length > 0 ? (
            <>
              <Button variant="secondary" onClick={() => onComplete('backlog')}>
                Move to Backlog
              </Button>
              <Button onClick={() => onComplete('rollover')}>
                Roll Over to Next Cycle
              </Button>
            </>
          ) : (
            <Button onClick={() => onComplete('backlog')}>Complete Cycle</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
