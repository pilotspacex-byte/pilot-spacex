'use client';

/**
 * Workflow Node Components — custom ReactFlow node renderers.
 *
 * Each of the 6 workflow node types has a dedicated component that renders:
 *   - Dark background card with type-specific border color
 *   - Lucide icon + label
 *   - Typed Handle components from WORKFLOW_NODE_SPECS
 *   - Selected state (thicker border + glow)
 *   - Validation error state (red border + dot indicator)
 *
 * Exports `workflowNodeTypes` map for ReactFlow's nodeTypes prop.
 */

import { memo, useContext } from 'react';
import { Handle, type NodeProps, type Node, type NodeTypes } from '@xyflow/react';
import {
  MessageSquare,
  Sparkles,
  GitBranch,
  ArrowRightLeft,
  ArrowDownToLine,
  ArrowUpFromLine,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import {
  WorkflowNodeType,
  WORKFLOW_NODE_SPECS,
  type WorkflowNodeData,
} from '@/features/skills/utils/graph-node-types';
import { GraphWorkflowContext } from '@/features/skills/contexts/graph-workflow-context';

// ── Icon Map ────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
  MessageSquare,
  Sparkles,
  GitBranch,
  ArrowRightLeft,
  ArrowDownToLine,
  ArrowUpFromLine,
};

// ── Shared Node Renderer ────────────────────────────────────────────────────

type WorkflowFlowNode = Node<WorkflowNodeData>;

interface WorkflowNodeInternalProps {
  nodeType: WorkflowNodeType;
  nodeId: string;
  data: WorkflowNodeData;
  selected?: boolean;
}

function WorkflowNodeInternal({ nodeType, nodeId, data, selected }: WorkflowNodeInternalProps) {
  const spec = WORKFLOW_NODE_SPECS[nodeType];
  const Icon = ICON_MAP[spec.icon] ?? MessageSquare;
  const hasError = !!data.validationError;

  // Read trace state from context (safe to read — component is inside ReactFlow tree)
  const ctx = useContext(GraphWorkflowContext);
  const traceState = ctx?.store.getNodeTraceState(nodeId) ?? null;

  const isTraceActive = traceState === 'active';
  const isTraceCompleted = traceState === 'completed';

  const borderColor = hasError
    ? '#ef4444'
    : isTraceActive
      ? spec.color
      : selected
        ? spec.color
        : `${spec.color}66`;
  const borderWidth = isTraceActive ? 2.5 : selected ? 2 : 1.5;
  const boxShadow = isTraceActive
    ? `0 0 16px 4px ${spec.color}55, 0 0 32px 8px ${spec.color}22`
    : selected
      ? `0 0 12px 2px ${spec.color}33`
      : hasError
        ? '0 0 8px 1px rgba(239, 68, 68, 0.25)'
        : 'none';
  const opacity = isTraceCompleted ? 0.5 : 1;

  return (
    <div
      className="relative flex items-center gap-2.5 px-3 py-2.5 min-w-[140px] max-w-[200px]"
      style={{
        backgroundColor: '#1a1a2e',
        borderRadius: 12,
        border: `${borderWidth}px solid ${borderColor}`,
        boxShadow,
        opacity,
        transition: 'border-color 150ms ease, box-shadow 300ms ease, opacity 300ms ease',
        animation: isTraceActive ? 'nodeTracePulse 1.2s ease-in-out infinite' : undefined,
      }}
    >
      {/* Handles */}
      {spec.handles.map((handle) => (
        <Handle
          key={handle.id}
          id={handle.id}
          type={handle.type}
          position={handle.position}
          style={{
            width: 10,
            height: 10,
            backgroundColor: handle.dataType === 'boolean'
              ? (handle.id.endsWith(':true') ? '#22c55e' : '#ef4444')
              : spec.color,
            border: '2px solid #1a1a2e',
            ...handle.style,
          }}
        />
      ))}

      {/* Icon */}
      <span
        className="shrink-0 flex items-center justify-center rounded-md"
        style={{
          width: 28,
          height: 28,
          backgroundColor: `${spec.color}22`,
        }}
      >
        <Icon width={16} height={16} style={{ color: spec.color }} strokeWidth={1.8} />
      </span>

      {/* Label */}
      <span
        className="text-sm font-medium truncate"
        style={{ color: '#e2e8f0' }}
      >
        {data.label}
      </span>

      {/* Trace step indicator */}
      {isTraceActive && (
        <span
          className="absolute -top-2 -left-2 flex items-center justify-center rounded-full text-[9px] font-bold"
          style={{
            width: 18,
            height: 18,
            backgroundColor: spec.color,
            color: '#fff',
          }}
        >
          {ctx?.store.activeTraceStep !== null && ctx?.store.activeTraceStep !== undefined
            ? ctx.store.activeTraceStep + 1
            : ''}
        </span>
      )}

      {/* Completed check overlay */}
      {isTraceCompleted && (
        <span
          className="absolute -top-1.5 -right-1.5 flex items-center justify-center rounded-full text-[10px]"
          style={{
            width: 16,
            height: 16,
            backgroundColor: '#22c55e',
            color: '#fff',
          }}
        >
          ✓
        </span>
      )}

      {/* Validation error dot */}
      {hasError && !isTraceActive && !isTraceCompleted && (
        <span
          className="absolute -top-1 -right-1 size-2.5 rounded-full"
          style={{ backgroundColor: '#ef4444' }}
          title={data.validationError}
        />
      )}

      {/* Pulse animation keyframes */}
      {isTraceActive && (
        <style>{`
          @keyframes nodeTracePulse {
            0%, 100% { box-shadow: 0 0 16px 4px ${spec.color}55, 0 0 32px 8px ${spec.color}22; }
            50% { box-shadow: 0 0 24px 8px ${spec.color}77, 0 0 48px 16px ${spec.color}33; }
          }
        `}</style>
      )}
    </div>
  );
}

// ── Per-Type Components ─────────────────────────────────────────────────────

const PromptNode = memo(function PromptNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Prompt} nodeId={id} data={data} selected={selected} />;
});

const SkillNode = memo(function SkillNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Skill} nodeId={id} data={data} selected={selected} />;
});

const ConditionNode = memo(function ConditionNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Condition} nodeId={id} data={data} selected={selected} />;
});

const TransformNode = memo(function TransformNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Transform} nodeId={id} data={data} selected={selected} />;
});

const InputNode = memo(function InputNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Input} nodeId={id} data={data} selected={selected} />;
});

const OutputNode = memo(function OutputNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  return <WorkflowNodeInternal nodeType={WorkflowNodeType.Output} nodeId={id} data={data} selected={selected} />;
});

// ── nodeTypes map for ReactFlow ─────────────────────────────────────────────

export const workflowNodeTypes: NodeTypes = {
  [WorkflowNodeType.Prompt]: PromptNode as NodeTypes[string],
  [WorkflowNodeType.Skill]: SkillNode as NodeTypes[string],
  [WorkflowNodeType.Condition]: ConditionNode as NodeTypes[string],
  [WorkflowNodeType.Transform]: TransformNode as NodeTypes[string],
  [WorkflowNodeType.Input]: InputNode as NodeTypes[string],
  [WorkflowNodeType.Output]: OutputNode as NodeTypes[string],
};
