'use client';

/**
 * PMBlockNodeView — React NodeView wrapper that dispatches to type-specific renderers.
 *
 * This is the bridge between TipTap's PMBlockExtension (atom node) and
 * the React renderer components (DecisionRenderer, FormRenderer, etc.).
 *
 * Each blockType maps to a lazy-loaded renderer. Unknown types show a fallback.
 *
 * @module pm-blocks/PMBlockNodeView
 */
import {
  type ComponentType,
  Component,
  Suspense,
  lazy,
  useMemo,
  useCallback,
  useState,
} from 'react';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { AlertTriangle, RotateCcw, Code } from 'lucide-react';
import { pmBlockStyles } from './pm-block-styles';
import type { PMBlockType } from './PMBlockExtension';
import { useBlockEditGuard } from './shared/useBlockEditGuard';

/** Lazy-loaded renderer registry — one per block type. */
const RENDERER_MAP: Record<PMBlockType, ComponentType<PMRendererProps>> = {
  decision: lazy(() =>
    import('./renderers/DecisionRenderer').then((m) => ({ default: m.DecisionRenderer }))
  ),
  form: lazy(() => import('./renderers/FormRenderer').then((m) => ({ default: m.FormRenderer }))),
  raci: lazy(() => import('./renderers/RACIRenderer').then((m) => ({ default: m.RACIRenderer }))),
  risk: lazy(() => import('./renderers/RiskRenderer').then((m) => ({ default: m.RiskRenderer }))),
  timeline: lazy(() =>
    import('./renderers/TimelineRenderer').then((m) => ({ default: m.TimelineRenderer }))
  ),
  dashboard: lazy(() =>
    import('./renderers/DashboardRenderer').then((m) => ({ default: m.DashboardRenderer }))
  ),
  // Feature 017 — PM Block Engine (T-228): renderers TBD
  'sprint-board': lazy(() =>
    import('./renderers/SprintBoardRenderer').then((m) => ({ default: m.SprintBoardRenderer }))
  ),
  'dependency-map': lazy(() =>
    import('./renderers/DependencyMapRenderer').then((m) => ({ default: m.DependencyMapRenderer }))
  ),
  'capacity-plan': lazy(() =>
    import('./renderers/CapacityPlanRenderer').then((m) => ({ default: m.CapacityPlanRenderer }))
  ),
  'release-notes': lazy(() =>
    import('./renderers/ReleaseNotesRenderer').then((m) => ({ default: m.ReleaseNotesRenderer }))
  ),
};

/** Props passed to every type-specific renderer. */
export interface PMRendererProps {
  /** The parsed JSON data for this block. */
  data: Record<string, unknown>;
  /** Whether the editor is in read-only mode. */
  readOnly: boolean;
  /** Callback to update the block's data JSON (marks block as user-edited via edit guard). */
  onDataChange: (newData: Record<string, unknown>) => void;
  /** The block type (for renderers that handle multiple sub-types). */
  blockType: PMBlockType;
  /** Callback to create an issue from block context (e.g., decided decision). */
  onCreateIssue?: (context: { blockType: PMBlockType; data: Record<string, unknown> }) => void;
}

/** Block type display labels for the type badge. */
const BLOCK_TYPE_LABELS: Record<PMBlockType, string> = {
  decision: 'Decision Record',
  form: 'Form',
  raci: 'RACI Matrix',
  risk: 'Risk Register',
  timeline: 'Timeline',
  dashboard: 'KPI Dashboard',
  // Feature 017 — PM Block Engine (T-228)
  'sprint-board': 'Sprint Board',
  'dependency-map': 'Dependency Map',
  'capacity-plan': 'Capacity Plan',
  'release-notes': 'Release Notes',
};

/** Loading skeleton shown while renderer chunk loads. */
function RendererSkeleton() {
  return (
    <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
      Loading block...
    </div>
  );
}

/** Fallback for unknown block types. */
function UnknownBlockFallback({ blockType }: { blockType: string }) {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
      <AlertTriangle className="size-4 text-amber-500" />
      <span>
        Unknown block type: <code>{blockType}</code>
      </span>
    </div>
  );
}

/** Error boundary fallback UI with retry and raw data toggle. */
function ErrorFallback({
  error,
  onRetry,
  rawData,
}: {
  error: Error;
  onRetry: () => void;
  rawData: string;
}) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="flex flex-col gap-2 p-4 text-sm" role="alert">
      <div className="flex items-center gap-2 text-destructive">
        <AlertTriangle className="size-4 shrink-0" />
        <span>Block renderer crashed: {error.message}</span>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-accent"
          onClick={onRetry}
        >
          <RotateCcw className="size-3" />
          Retry
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-accent"
          onClick={() => setShowRaw((v) => !v)}
        >
          <Code className="size-3" />
          {showRaw ? 'Hide' : 'Show'} raw data
        </button>
      </div>
      {showRaw && (
        <pre className="max-h-40 overflow-auto rounded-md bg-muted p-2 text-xs">{rawData}</pre>
      )}
    </div>
  );
}

/** Error boundary wrapping PM block renderers to prevent editor crash. */
class PMBlockErrorBoundary extends Component<
  { children: React.ReactNode; rawData: string },
  { error: Error | null; errorKey: number }
> {
  state = { error: null as Error | null, errorKey: 0 };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  handleRetry = () => {
    this.setState((prev) => ({ error: null, errorKey: prev.errorKey + 1 }));
  };

  render() {
    if (this.state.error) {
      return (
        <ErrorFallback
          error={this.state.error}
          onRetry={this.handleRetry}
          rawData={this.props.rawData}
        />
      );
    }
    return <div key={this.state.errorKey}>{this.props.children}</div>;
  }
}

/**
 * PMBlockNodeView — TipTap React NodeView component.
 *
 * Reads `blockType` and `data` attrs from the ProseMirror node,
 * dispatches to the correct lazy-loaded renderer.
 */
export function PMBlockNodeView({ node, updateAttributes, editor }: NodeViewProps) {
  const blockType = (node.attrs.blockType as PMBlockType) || 'decision';
  const rawData = (node.attrs.data as string) || '{}';
  const blockId = (node.attrs.blockId as string) || '';
  const readOnly = !editor.isEditable;

  const { markEdited } = useBlockEditGuard(editor);

  const data = useMemo<Record<string, unknown>>(() => {
    try {
      return JSON.parse(rawData);
    } catch {
      return {};
    }
  }, [rawData]);

  const onDataChange = useCallback(
    (newData: Record<string, unknown>) => {
      if (blockId) markEdited(blockId);
      updateAttributes({ data: JSON.stringify(newData) });
    },
    [updateAttributes, blockId, markEdited]
  );

  const onCreateIssue = useCallback(
    (context: { blockType: PMBlockType; data: Record<string, unknown> }) => {
      document.dispatchEvent(
        new CustomEvent('pm-block:create-issue', { detail: { ...context, blockId } })
      );
    },
    [blockId]
  );

  const Renderer = RENDERER_MAP[blockType];
  const label = BLOCK_TYPE_LABELS[blockType] || blockType;

  return (
    <NodeViewWrapper
      className={pmBlockStyles.shared.wrapper}
      role="region"
      aria-label={`${label} block`}
    >
      {/* Type badge */}
      <span className={pmBlockStyles.shared.typeLabel}>{label}</span>

      {/* Mobile read-only indicator */}
      {readOnly && <span className={pmBlockStyles.shared.mobileReadOnly}>Read-only</span>}

      {/* Content area */}
      <div className={pmBlockStyles.shared.content}>
        {Renderer ? (
          <PMBlockErrorBoundary rawData={rawData}>
            <Suspense fallback={<RendererSkeleton />}>
              <Renderer
                data={data}
                readOnly={readOnly}
                onDataChange={onDataChange}
                blockType={blockType}
                onCreateIssue={onCreateIssue}
              />
            </Suspense>
          </PMBlockErrorBoundary>
        ) : (
          <UnknownBlockFallback blockType={blockType} />
        )}
      </div>
    </NodeViewWrapper>
  );
}
