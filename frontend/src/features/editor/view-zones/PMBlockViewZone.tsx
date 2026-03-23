'use client';

/**
 * PMBlockViewZone - React component rendered inside Monaco view zones.
 *
 * NOT wrapped in observer() - plain React component due to React 19
 * flushSync constraint (see project memory: IssueEditorContent constraint).
 *
 * Lazy-loads the appropriate PM block renderer based on block type.
 * Supports collapse/expand toggle with 200ms height transition.
 */

import { lazy, Suspense, useState, useCallback, type JSX } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import type { PMBlockType } from '../types';

/* ── Lazy renderer registry ───────────────────────────────────────── */

const rendererMap: Record<
  PMBlockType,
  React.LazyExoticComponent<React.ComponentType<Record<string, unknown>>>
> = {
  decision: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/DecisionRenderer').then((m) => ({
      default: m.DecisionRenderer as unknown as React.ComponentType<Record<string, unknown>>,
    }))
  ),
  raci: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/RACIRenderer').then((m) => ({
      default: m.RACIRenderer as unknown as React.ComponentType<Record<string, unknown>>,
    }))
  ),
  risk: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/RiskRenderer').then((m) => ({
      default: m.RiskRenderer as unknown as React.ComponentType<Record<string, unknown>>,
    }))
  ),
  dependency: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/DependencyMapRenderer').then(
      (m) => ({
        default: m.DependencyMapRenderer as unknown as React.ComponentType<Record<string, unknown>>,
      })
    )
  ),
  timeline: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/TimelineRenderer').then((m) => ({
      default: m.TimelineRenderer as unknown as React.ComponentType<Record<string, unknown>>,
    }))
  ),
  'sprint-board': lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/SprintBoardRenderer').then(
      (m) => ({
        default: m.SprintBoardRenderer as unknown as React.ComponentType<Record<string, unknown>>,
      })
    )
  ),
  dashboard: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/DashboardRenderer').then(
      (m) => ({
        default: m.DashboardRenderer as unknown as React.ComponentType<Record<string, unknown>>,
      })
    )
  ),
  form: lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/FormRenderer').then((m) => ({
      default: m.FormRenderer as unknown as React.ComponentType<Record<string, unknown>>,
    }))
  ),
  'release-notes': lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/ReleaseNotesRenderer').then(
      (m) => ({
        default: m.ReleaseNotesRenderer as unknown as React.ComponentType<Record<string, unknown>>,
      })
    )
  ),
  'capacity-plan': lazy(() =>
    import('@/features/notes/editor/extensions/pm-blocks/renderers/CapacityPlanRenderer').then(
      (m) => ({
        default: m.CapacityPlanRenderer as unknown as React.ComponentType<Record<string, unknown>>,
      })
    )
  ),
};

/* ── Block type display labels ────────────────────────────────────── */

const BLOCK_TYPE_LABELS: Record<PMBlockType, string> = {
  decision: 'Decision Record',
  raci: 'RACI Matrix',
  risk: 'Risk Register',
  dependency: 'Dependency Map',
  timeline: 'Timeline',
  'sprint-board': 'Sprint Board',
  dashboard: 'Dashboard',
  form: 'Form',
  'release-notes': 'Release Notes',
  'capacity-plan': 'Capacity Plan',
};

/* ── Component ────────────────────────────────────────────────────── */

interface PMBlockViewZoneProps {
  type: PMBlockType;
  data: Record<string, unknown> | null;
  raw: string;
}

/**
 * View zone component for rendering PM blocks inside Monaco editor.
 * Plain React component (NOT observer-wrapped).
 */
export function PMBlockViewZone({ type, data, raw }: PMBlockViewZoneProps): JSX.Element {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleToggle = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  const Renderer = rendererMap[type];
  const label = BLOCK_TYPE_LABELS[type] ?? type;

  // Adapter: PMRendererProps expects { data, readOnly, onDataChange, blockType }
  const rendererProps: Record<string, unknown> = {
    data: data ?? {},
    readOnly: true,
    onDataChange: () => {
      /* view zones are read-only in Monaco context */
    },
    blockType: type,
  };

  return (
    <div
      className={cn(
        'bg-background-subtle border-y border-border-subtle p-4 min-h-[80px]',
        'transition-[height] duration-200 ease-in-out overflow-hidden'
      )}
    >
      {/* Header with collapse toggle */}
      <button
        type="button"
        onClick={handleToggle}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-2 w-full text-left"
        aria-expanded={!isCollapsed}
        aria-label={`${isCollapsed ? 'Expand' : 'Collapse'} ${label}`}
      >
        <ChevronDown
          className={cn('h-4 w-4 transition-transform duration-200', isCollapsed && '-rotate-90')}
        />
        <span className="font-medium">{label}</span>
      </button>

      {/* Content */}
      {!isCollapsed && (
        <Suspense fallback={<Skeleton className="h-20 w-full" />}>
          {Renderer ? (
            <Renderer {...rendererProps} />
          ) : (
            <pre className="text-xs text-muted-foreground">{raw}</pre>
          )}
        </Suspense>
      )}
    </div>
  );
}
