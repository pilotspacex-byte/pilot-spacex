'use client';

import * as React from 'react';

// ============================================================================
// Types
// ============================================================================

interface GraphTask {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  sortOrder: number;
  dependencyIds: string[];
}

export interface TaskDependencyGraphProps {
  tasks: GraphTask[];
  /** Show loading skeleton */
  isLoading?: boolean;
}

// ============================================================================
// Layout helpers
// ============================================================================

interface NodePosition {
  x: number;
  y: number;
  task: GraphTask;
  index: number;
}

function computeDepthMap(tasks: GraphTask[]): Map<string, number> {
  const taskMap = new Map(tasks.map((t) => [t.id, t]));
  const depths = new Map<string, number>();
  const visiting = new Set<string>();

  function getDepth(id: string): number {
    const cached = depths.get(id);
    if (cached !== undefined) return cached;
    if (visiting.has(id)) return 0; // cycle guard
    visiting.add(id);

    const task = taskMap.get(id);
    if (!task || task.dependencyIds.length === 0) {
      depths.set(id, 0);
      visiting.delete(id);
      return 0;
    }

    const maxParentDepth = Math.max(
      ...task.dependencyIds.filter((depId) => taskMap.has(depId)).map((depId) => getDepth(depId))
    );
    const depth = maxParentDepth + 1;
    depths.set(id, depth);
    visiting.delete(id);
    return depth;
  }

  tasks.forEach((t) => getDepth(t.id));
  return depths;
}

function computeNodePositions(
  tasks: GraphTask[],
  canvasWidth: number,
  canvasHeight: number
): NodePosition[] {
  if (tasks.length === 0) return [];
  if (tasks.length === 1) {
    return [{ x: canvasWidth / 2, y: canvasHeight / 2, task: tasks[0]!, index: 0 }];
  }

  const depthMap = computeDepthMap(tasks);
  const maxDepth = Math.max(...depthMap.values(), 0);

  // Group by depth
  const depthGroups = new Map<number, GraphTask[]>();
  tasks.forEach((t) => {
    const d = depthMap.get(t.id) ?? 0;
    const group = depthGroups.get(d) ?? [];
    group.push(t);
    depthGroups.set(d, group);
  });

  const positions: NodePosition[] = [];
  const xStep = maxDepth === 0 ? 0 : Math.min(140, (canvasWidth - 160) / maxDepth);

  depthGroups.forEach((group, depth) => {
    const x = 80 + depth * xStep;
    const spacing = Math.min(50, (canvasHeight - 40) / (group.length + 1));

    group.forEach((task, i) => {
      const centerOffset = (i - (group.length - 1) / 2) * spacing;
      const y = canvasHeight / 2 + centerOffset;
      positions.push({ x, y, task, index: positions.length });
    });
  });

  return positions;
}

// ============================================================================
// Drawing
// ============================================================================

const NODE_RADIUS = 24;
const ROOT_COLOR = '#6B8FAD';
const DEFAULT_COLOR = '#29A386';
const DONE_COLOR = '#22c55e';
const EDGE_COLOR = '#B8CCDB';
const ARROW_SIZE = 8;

function drawGraph(ctx: CanvasRenderingContext2D, positions: NodePosition[], tasks: GraphTask[]) {
  const posMap = new Map(positions.map((p) => [p.task.id, p]));

  // Draw edges
  ctx.strokeStyle = EDGE_COLOR;
  ctx.lineWidth = 2;
  ctx.fillStyle = EDGE_COLOR;

  tasks.forEach((task) => {
    const target = posMap.get(task.id);
    if (!target) return;

    task.dependencyIds.forEach((depId) => {
      const source = posMap.get(depId);
      if (!source) return;

      const sx = source.x + NODE_RADIUS + 6;
      const sy = source.y;
      const tx = target.x - NODE_RADIUS - 6;
      const ty = target.y;

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.stroke();

      // Arrow head
      const angle = Math.atan2(ty - sy, tx - sx);
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(
        tx - ARROW_SIZE * Math.cos(angle - Math.PI / 6),
        ty - ARROW_SIZE * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        tx - ARROW_SIZE * Math.cos(angle + Math.PI / 6),
        ty - ARROW_SIZE * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fill();
    });
  });

  // Draw nodes
  positions.forEach((pos) => {
    const isRoot = pos.task.dependencyIds.length === 0;
    const isDone = pos.task.status === 'done';

    let fill = isRoot ? ROOT_COLOR : DEFAULT_COLOR;
    if (isDone) fill = DONE_COLOR;

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();

    // Node number
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '600 12px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${pos.index + 1}`, pos.x, pos.y);

    // Label below
    ctx.fillStyle = '#171717';
    ctx.font = '500 10px system-ui, sans-serif';
    ctx.textBaseline = 'top';
    const label =
      pos.task.title.length > 12 ? pos.task.title.slice(0, 11) + '\u2026' : pos.task.title;
    ctx.fillText(label, pos.x, pos.y + 34);
  });
}

// ============================================================================
// Accessibility description
// ============================================================================

function buildDescription(tasks: GraphTask[]): string {
  const indexById = new Map(tasks.map((t, i) => [t.id, i + 1]));
  const lines = tasks.map((t, i) => {
    const deps =
      t.dependencyIds.length > 0
        ? ` depends on task ${t.dependencyIds.map((depId) => indexById.get(depId) ?? '?').join(', ')}`
        : ' (root task)';
    return `Task ${i + 1}: ${t.title}, status ${t.status}${deps}`;
  });
  return lines.join('. ');
}

// ============================================================================
// Component
// ============================================================================

export function TaskDependencyGraph({ tasks, isLoading }: TaskDependencyGraphProps) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const hasDependencies = tasks.some((t) => t.dependencyIds.length > 0);

  React.useEffect(() => {
    if (!hasDependencies || isLoading) return;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const width = container.offsetWidth;
    const height = container.offsetHeight;
    const dpr = window.devicePixelRatio || 2;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const positions = computeNodePositions(tasks, width, height);
    drawGraph(ctx, positions, tasks);
  }, [tasks, hasDependencies, isLoading]);

  if (isLoading) {
    return (
      <div
        className="h-[200px] bg-muted/30 border border-border rounded-[10px] animate-pulse"
        role="status"
        aria-label="Loading dependency graph"
      />
    );
  }

  if (!hasDependencies || tasks.length === 0) {
    return null;
  }

  const description = buildDescription(tasks);

  return (
    <div
      ref={containerRef}
      className="h-[200px] bg-muted/30 border border-border rounded-[10px] overflow-hidden max-sm:h-[150px]"
      data-testid="task-dependency-graph"
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        role="img"
        aria-label={`Task dependency graph showing ${tasks.length} tasks`}
      />
      <div className="sr-only">{description}</div>
    </div>
  );
}
