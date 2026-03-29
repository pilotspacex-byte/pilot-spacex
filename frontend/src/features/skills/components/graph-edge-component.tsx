'use client';

/**
 * graph-edge-component — Custom edge renderers for the workflow graph editor.
 *
 * Three edge types with distinct visual styles:
 * - Sequential: solid bezier with animated flow + arrow marker
 * - Conditional: colored green (Yes) / red (No) with labels
 * - Loop: dashed purple with "Loop" label
 */

import { type FC } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
  type Edge,
} from '@xyflow/react';

// Semantic edge colors — use CSS custom properties from design tokens where possible
const EDGE_COLORS = {
  sequential: 'hsl(var(--muted-foreground))',
  sequentialFlow: 'hsl(var(--muted-foreground) / 0.7)',
  conditionTrue: 'hsl(var(--primary))',          // teal-green #29A386
  conditionFalse: 'hsl(var(--destructive))',      // warm-red #D9534F
  loop: '#8B7EC8',                                // in-review purple from design system
} as const;

// ── Edge data types ────────────────────────────────────────────────────────

export interface ConditionalEdgeData extends Record<string, unknown> {
  branch?: 'true' | 'false';
}

export interface LoopEdgeData extends Record<string, unknown> {
  label?: string;
}

// ── Sequential Edge ────────────────────────────────────────────────────────

const SequentialEdge: FC<EdgeProps<Edge<Record<string, unknown>>>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd: _markerEnd,
  ...rest
}) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      {/* Background path for visibility */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: EDGE_COLORS.sequential,
          strokeWidth: 2,
        }}
        markerEnd={`url(#marker-sequential-${id})`}
        {...rest}
      />
      {/* Animated flow overlay */}
      <path
        d={edgePath}
        fill="none"
        stroke={EDGE_COLORS.sequentialFlow}
        strokeWidth={2}
        strokeDasharray="6 4"
        className="animate-edge-flow"
        style={{
          animation: 'edgeFlow 1.5s linear infinite',
        }}
      />
      {/* Arrow marker definition */}
      <defs>
        <marker
          id={`marker-sequential-${id}`}
          viewBox="0 0 12 12"
          refX="10"
          refY="6"
          markerWidth="8"
          markerHeight="8"
          orient="auto-start-reverse"
        >
          <path d="M 2 2 L 10 6 L 2 10 Z" fill="#64748b" />
        </marker>
      </defs>
      <style>{`
        @keyframes edgeFlow {
          to { stroke-dashoffset: -20; }
        }
      `}</style>
    </>
  );
};

// ── Conditional Edge ───────────────────────────────────────────────────────

const ConditionalEdge: FC<EdgeProps<Edge<ConditionalEdgeData>>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  ...rest
}) => {
  const branch = data?.branch ?? 'true';
  const isTrueBranch = branch === 'true';
  const edgeColor = isTrueBranch ? EDGE_COLORS.conditionTrue : EDGE_COLORS.conditionFalse;
  const labelText = isTrueBranch ? 'Yes' : 'No';

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: edgeColor,
          strokeWidth: 2,
        }}
        markerEnd={`url(#marker-conditional-${id})`}
        {...rest}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-none absolute rounded-full px-2 py-0.5 text-xs font-semibold"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            backgroundColor: edgeColor,
            color: '#fff',
          }}
        >
          {labelText}
        </div>
      </EdgeLabelRenderer>
      <defs>
        <marker
          id={`marker-conditional-${id}`}
          viewBox="0 0 12 12"
          refX="10"
          refY="6"
          markerWidth="8"
          markerHeight="8"
          orient="auto-start-reverse"
        >
          <path d="M 2 2 L 10 6 L 2 10 Z" fill={edgeColor} />
        </marker>
      </defs>
    </>
  );
};

// ── Loop Edge ──────────────────────────────────────────────────────────────

const LoopEdge: FC<EdgeProps<Edge<LoopEdgeData>>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  ...rest
}) => {
  const labelText = data?.label ?? 'Loop';

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: EDGE_COLORS.loop,
          strokeWidth: 2,
          strokeDasharray: '8 4',
        }}
        markerEnd={`url(#marker-loop-${id})`}
        {...rest}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-none absolute rounded-full px-2 py-0.5 text-xs font-semibold"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            backgroundColor: EDGE_COLORS.loop,
            color: '#fff',
          }}
        >
          {labelText}
        </div>
      </EdgeLabelRenderer>
      <defs>
        <marker
          id={`marker-loop-${id}`}
          viewBox="0 0 12 12"
          refX="10"
          refY="6"
          markerWidth="8"
          markerHeight="8"
          orient="auto-start-reverse"
        >
          <path d="M 2 2 L 10 6 L 2 10 Z" fill="#a855f7" />
        </marker>
      </defs>
    </>
  );
};

// ── Export edge types map ──────────────────────────────────────────────────

export const workflowEdgeTypes = {
  sequential: SequentialEdge,
  conditional: ConditionalEdge,
  loop: LoopEdge,
} as const;
