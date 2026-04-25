'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  LayoutGrid,
  List,
  Table2,
  Plus,
  Rows3,
  Rows2,
  Minus,
  BarChart2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useIssueViewStore } from '@/stores/RootStore';
import { FilterBar } from './FilterBar';

interface IssueToolbarProps {
  hideProjectFilter?: boolean;
  projectId?: string;
  assigneeOptions?: Array<{ value: string; label: string }>;
  labelOptions?: Array<{ value: string; label: string; color?: string }>;
  projectOptions?: Array<{ value: string; label: string }>;
  onCreateIssue?: () => void;
}

const VIEW_MODES = [
  { key: 'board' as const, icon: LayoutGrid, label: 'Board' },
  { key: 'list' as const, icon: List, label: 'List' },
  { key: 'table' as const, icon: Table2, label: 'Table' },
  { key: 'priority' as const, icon: BarChart2, label: 'Priority' },
];

const DENSITY_OPTIONS = [
  { key: 'comfortable' as const, icon: Rows3, label: 'Comfortable' },
  { key: 'compact' as const, icon: Rows2, label: 'Compact' },
  { key: 'minimal' as const, icon: Minus, label: 'Minimal' },
];

export const IssueToolbar = observer(function IssueToolbar({
  hideProjectFilter,
  projectId,
  assigneeOptions,
  labelOptions,
  projectOptions,
  onCreateIssue,
}: IssueToolbarProps) {
  const viewStore = useIssueViewStore();

  return (
    <div className="flex flex-col gap-3 px-4 py-3 border-b">
      <div className="flex items-center justify-between gap-3">
        {/* Left: View toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border bg-muted/30 p-0.5">
            {VIEW_MODES.map(({ key, icon: ModeIcon, label }) => (
              <button
                key={key}
                onClick={() => viewStore.setEffectiveViewMode(key, projectId)}
                className={cn(
                  'flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors',
                  viewStore.getEffectiveViewMode(projectId) === key
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
                aria-label={`Switch to ${label} view`}
                aria-pressed={viewStore.getEffectiveViewMode(projectId) === key}
              >
                <ModeIcon className="size-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right: Density + Create */}
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs">
                {DENSITY_OPTIONS.find((d) => d.key === viewStore.cardDensity)?.icon &&
                  React.createElement(
                    DENSITY_OPTIONS.find((d) => d.key === viewStore.cardDensity)!.icon,
                    { className: 'size-3.5' }
                  )}
                <span className="hidden sm:inline">Density</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {DENSITY_OPTIONS.map(({ key, icon: DIcon, label }) => (
                <DropdownMenuItem
                  key={key}
                  onClick={() => viewStore.setCardDensity(key)}
                  className={cn(viewStore.cardDensity === key && 'bg-accent')}
                >
                  <DIcon className="mr-2 size-4" />
                  {label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {onCreateIssue && (
            <Button onClick={onCreateIssue} size="sm" className="h-7 gap-1.5 text-xs">
              <Plus className="size-3.5" />
              <span className="hidden sm:inline">New Task</span>
            </Button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        hideProjectFilter={hideProjectFilter}
        assigneeOptions={assigneeOptions}
        labelOptions={labelOptions}
        projectOptions={projectOptions}
      />
    </div>
  );
});
