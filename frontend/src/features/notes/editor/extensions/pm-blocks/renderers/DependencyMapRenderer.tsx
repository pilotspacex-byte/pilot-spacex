'use client';

/**
 * DependencyMapRenderer — Dependency map PM block renderer.
 *
 * FR-051: DAG with critical path highlighting.
 * FR-052: Zoom/pan for 20+ nodes.
 * FR-056–059: AI insight badge.
 *
 * Data shape (stored in block.data):
 *   { workspaceId: string, cycleId: string, title?: string }
 *
 * @module pm-blocks/renderers/DependencyMapRenderer
 */
import { useCallback, useMemo, useRef, useState, WheelEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Loader2, RefreshCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlocksApi } from '@/services/api/pm-blocks';
import { pmBlockStyles } from '../pm-block-styles';
import { AIInsightBadge } from '../shared/AIInsightBadge';
import type { PMRendererProps } from '../PMBlockNodeView';
import type {
  DepMapNode,
  DepMapEdge,
  DependencyMapData,
  PMBlockInsight,
} from '@/services/api/pm-blocks';

// ── Layout helpers ────────────────────────────────────────────────────────────

const NODE_W = 140;
const NODE_H = 48;
const COL_GAP = 60;
const ROW_GAP = 20;

/** Simple layered layout: topological sort → assign x,y per layer. */
function computeLayout(
  nodes: DepMapNode[],
  edges: DepMapEdge[]
): Map<string, { x: number; y: number }> {
  const inDegree = new Map<string, number>(nodes.map((n) => [n.id, 0]));
  const adj = new Map<string, string[]>(nodes.map((n) => [n.id, []]));

  for (const e of edges) {
    inDegree.set(e.targetId, (inDegree.get(e.targetId) ?? 0) + 1);
    adj.get(e.sourceId)?.push(e.targetId);
  }

  // Kahn's algorithm for topological sort by layer
  const layers: string[][] = [];
  let queue = [...inDegree.entries()].filter(([, d]) => d === 0).map(([id]) => id);

  while (queue.length) {
    layers.push(queue);
    const nextQueue: string[] = [];
    for (const id of queue) {
      for (const neighbor of adj.get(id) ?? []) {
        const deg = (inDegree.get(neighbor) ?? 0) - 1;
        inDegree.set(neighbor, deg);
        if (deg === 0) nextQueue.push(neighbor);
      }
    }
    queue = nextQueue;
  }

  // Nodes not reachable (circular deps) go in last layer
  const placed = new Set(layers.flat());
  const leftover = nodes.filter((n) => !placed.has(n.id)).map((n) => n.id);
  if (leftover.length) layers.push(leftover);

  const positions = new Map<string, { x: number; y: number }>();
  layers.forEach((layer, col) => {
    layer.forEach((id, row) => {
      positions.set(id, {
        x: col * (NODE_W + COL_GAP),
        y: row * (NODE_H + ROW_GAP),
      });
    });
  });

  return positions;
}

// ── State group → fill color ──────────────────────────────────────────────────

const STATE_GROUP_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  completed: { fill: '#29A38618', stroke: '#29A386', text: '#29A386' },
  started: { fill: '#D9853F18', stroke: '#D9853F', text: '#D9853F' },
  unstarted: {
    fill: 'hsl(var(--muted))',
    stroke: 'hsl(var(--border))',
    text: 'hsl(var(--muted-foreground))',
  },
  cancelled: {
    fill: 'transparent',
    stroke: 'hsl(var(--border))',
    text: 'hsl(var(--muted-foreground)/0.5)',
  },
};

// ── DAG SVG ───────────────────────────────────────────────────────────────────

interface DAGSVGProps {
  data: DependencyMapData;
  width: number;
  height: number;
  criticalSet: Set<string>;
}

function DAGSVG({ data, width, height, criticalSet }: DAGSVGProps) {
  const positions = useMemo(() => computeLayout(data.nodes, data.edges), [data.nodes, data.edges]);

  return (
    <svg
      width={width}
      height={height}
      aria-label="Dependency map"
      role="img"
      className="overflow-visible"
    >
      <defs>
        <marker id="arrow-normal" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="hsl(var(--muted-foreground)/0.4)" />
        </marker>
        <marker
          id="arrow-critical"
          markerWidth="6"
          markerHeight="6"
          refX="5"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill="#D9534F" />
        </marker>
      </defs>

      {/* Edges */}
      {data.edges.map((edge, i) => {
        const src = positions.get(edge.sourceId);
        const tgt = positions.get(edge.targetId);
        if (!src || !tgt) return null;
        const isCritical = edge.isCritical;
        const x1 = src.x + NODE_W;
        const y1 = src.y + NODE_H / 2;
        const x2 = tgt.x;
        const y2 = tgt.y + NODE_H / 2;
        const mx = (x1 + x2) / 2;

        return (
          <path
            key={`edge-${i}`}
            d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
            fill="none"
            stroke={isCritical ? '#D9534F' : 'hsl(var(--muted-foreground)/0.35)'}
            strokeWidth={isCritical ? 2 : 1}
            strokeDasharray={isCritical ? undefined : '4 3'}
            markerEnd={isCritical ? 'url(#arrow-critical)' : 'url(#arrow-normal)'}
          />
        );
      })}

      {/* Nodes */}
      {data.nodes.map((node) => {
        const pos = positions.get(node.id);
        if (!pos) return null;
        const isOnCritical = criticalSet.has(node.id);
        const colors = STATE_GROUP_COLORS[node.stateGroup] ?? STATE_GROUP_COLORS['unstarted']!;

        return (
          <g key={node.id} transform={`translate(${pos.x},${pos.y})`} aria-label={node.name}>
            <rect
              x={0}
              y={0}
              width={NODE_W}
              height={NODE_H}
              rx={8}
              ry={8}
              fill={colors.fill}
              stroke={isOnCritical ? '#D9534F' : colors.stroke}
              strokeWidth={isOnCritical ? 2 : 1}
            />
            <text
              x={NODE_W / 2}
              y={16}
              textAnchor="middle"
              fontSize={10}
              fontFamily="monospace"
              fill={colors.text}
            >
              {node.identifier}
            </text>
            <foreignObject x={4} y={20} width={NODE_W - 8} height={24}>
              <div
                style={{
                  fontSize: 10,
                  lineHeight: '12px',
                  overflow: 'hidden',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  color: 'hsl(var(--foreground))',
                  textAlign: 'center',
                }}
              >
                {node.name}
              </div>
            </foreignObject>
          </g>
        );
      })}
    </svg>
  );
}

// ── Block data types ──────────────────────────────────────────────────────────

interface DepMapBlockData {
  workspaceId?: string;
  cycleId?: string;
  title?: string;
}

// ── Query keys ────────────────────────────────────────────────────────────────

const QUERY_KEYS = {
  map: (workspaceId: string, cycleId: string) =>
    ['pm-blocks', 'dependency-map', workspaceId, cycleId] as const,
  insights: (workspaceId: string, blockId: string) =>
    ['pm-blocks', 'insights', workspaceId, blockId] as const,
};

// ── Main renderer ─────────────────────────────────────────────────────────────

const CANVAS_W = 900;
const CANVAS_H = 400;
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 2.0;
const ZOOM_STEP = 0.15;

export function DependencyMapRenderer({ data: rawData, readOnly: _readOnly }: PMRendererProps) {
  const data = rawData as DepMapBlockData;
  const workspaceId = data.workspaceId ?? '';
  const cycleId = data.cycleId ?? '';
  const blockId = `dependency-map-${cycleId}`;

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [panning, setPanning] = useState(false);
  const isPanning = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });
  const queryClient = useQueryClient();

  const {
    data: mapData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.map(workspaceId, cycleId),
    queryFn: () => pmBlocksApi.getDependencyMap(workspaceId, cycleId),
    enabled: Boolean(workspaceId && cycleId),
    staleTime: 60_000,
  });

  const { data: insights, isLoading: isInsightsLoading } = useQuery({
    queryKey: QUERY_KEYS.insights(workspaceId, blockId),
    queryFn: () => pmBlocksApi.listInsights(workspaceId, blockId),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const dismissMutation = useMutation({
    mutationFn: (insightId: string) => pmBlocksApi.dismissInsight(workspaceId, insightId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.insights(workspaceId, blockId) });
    },
  });

  const handleDismissInsight = useCallback(
    (insightId: string) => dismissMutation.mutate(insightId),
    [dismissMutation]
  );

  const topInsight = useMemo<PMBlockInsight | null>(() => {
    if (!insights?.length) return null;
    for (const sev of ['red', 'yellow', 'green'] as const) {
      const found = insights.find((i) => i.severity === sev && !i.dismissed);
      if (found) return found;
    }
    return null;
  }, [insights]);

  const criticalSet = useMemo(() => new Set(mapData?.criticalPath ?? []), [mapData]);

  const handleWheel = useCallback((e: WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    isPanning.current = true;
    setPanning(true);
    lastMouse.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPanning.current) return;
    setPan((p) => ({
      x: p.x + (e.clientX - lastMouse.current.x),
      y: p.y + (e.clientY - lastMouse.current.y),
    }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  }, []);

  const handleMouseUp = useCallback(() => {
    isPanning.current = false;
    setPanning(false);
  }, []);

  const resetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  if (!workspaceId || !cycleId) {
    return (
      <div className={pmBlockStyles.shared.container}>
        <div className={pmBlockStyles.shared.header}>
          <h3 className={pmBlockStyles.shared.title}>{data.title ?? 'Dependency Map'}</h3>
        </div>
        <p className="text-sm text-muted-foreground py-4 text-center">
          Configure workspace and cycle to display dependency map.
        </p>
      </div>
    );
  }

  return (
    <div className={pmBlockStyles.shared.container} data-testid="dependency-map-renderer">
      {/* Header */}
      <div className={pmBlockStyles.shared.header}>
        <h3 className={pmBlockStyles.shared.title}>{data.title ?? 'Dependency Map'}</h3>
        <div className="flex items-center gap-1.5">
          <AIInsightBadge
            insight={topInsight}
            insufficientData={!isInsightsLoading && !insights?.length}
            onDismiss={handleDismissInsight}
          />
          {/* Zoom controls — FR-052 */}
          <div className="flex items-center gap-0.5 rounded-md border border-border bg-muted/50">
            <button
              type="button"
              className="rounded-l-md p-1 hover:bg-accent transition-colors"
              onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP))}
              aria-label="Zoom out"
            >
              <ZoomOut className="size-3.5 text-muted-foreground" />
            </button>
            <span className="px-1.5 text-[11px] tabular-nums text-muted-foreground">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              className="p-1 hover:bg-accent transition-colors"
              onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP))}
              aria-label="Zoom in"
            >
              <ZoomIn className="size-3.5 text-muted-foreground" />
            </button>
            <button
              type="button"
              className="rounded-r-md p-1 hover:bg-accent transition-colors"
              onClick={resetView}
              aria-label="Reset view"
            >
              <Maximize2 className="size-3.5 text-muted-foreground" />
            </button>
          </div>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            onClick={() => refetch()}
            aria-label="Refresh dependency map"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Circular dependency warning — FR-051 */}
      {mapData?.hasCircular && (
        <div
          className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800/40 dark:bg-amber-900/10 dark:text-amber-400"
          role="alert"
        >
          <AlertTriangle className="size-3.5 shrink-0" />
          <span>
            Circular dependency detected:{' '}
            {mapData.circularDeps.map((cycle) => cycle.join(' → ')).join('; ')}
          </span>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="ml-2 text-sm">Loading dependency map...</span>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="py-4 text-center text-sm text-destructive">
          Failed to load dependency map.{' '}
          <button type="button" className="underline hover:no-underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* DAG canvas — FR-051/052 */}
      {mapData && !isLoading && (
        <>
          <div className="text-xs text-muted-foreground">
            {mapData.nodes.length} issues · {mapData.edges.length} dependencies
            {mapData.criticalPath.length > 0 && (
              <span className="ml-2 text-destructive">
                · Critical path: {mapData.criticalPath.length} issues
              </span>
            )}
          </div>

          <div
            className={cn(
              'relative overflow-hidden rounded-lg border border-border bg-muted/20',
              'cursor-grab active:cursor-grabbing select-none'
            )}
            style={{ height: 340 }}
            role="img"
            aria-label="Interactive dependency graph"
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <div
              style={{
                transform: `translate(${pan.x + 16}px, ${pan.y + 16}px) scale(${zoom})`,
                transformOrigin: '0 0',
                transition: panning ? 'none' : undefined,
              }}
            >
              <DAGSVG data={mapData} width={CANVAS_W} height={CANVAS_H} criticalSet={criticalSet} />
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="size-3 rounded border-2 border-destructive/70 bg-destructive/10" />
              Critical path
            </span>
            <span className="flex items-center gap-1">
              <span className="size-3 rounded border border-primary bg-primary/10" />
              Completed
            </span>
            <span className="flex items-center gap-1">
              <span className="size-3 rounded border border-[#D9853F] bg-[#D9853F]/10" />
              In progress
            </span>
            <span className="flex items-center gap-1">
              <span className="size-3 rounded border bg-muted" />
              Unstarted
            </span>
          </div>
        </>
      )}
    </div>
  );
}
