'use client';

/**
 * GraphConfigPanel — Slide-out configuration panel for workflow graph nodes.
 *
 * This component IS an observer() — it reads selectedNodeId from the
 * GraphWorkflowStore via context bridge. This is safe because the config
 * panel is OUTSIDE the ReactFlow canvas component tree (no flushSync issue).
 *
 * Shows type-specific form fields for each of the 6 workflow node types:
 * - Prompt: promptText (textarea), outputVar (input)
 * - Skill: skillTemplateId (input placeholder), overrideInstructions (input)
 * - Condition: expression (input) with hint
 * - Transform: template (textarea) with hint
 * - Input: paramName, paramType (select), description (textarea)
 * - Output: format (select), template (textarea)
 */

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import {
  MessageSquare,
  Sparkles,
  GitBranch,
  ArrowRightLeft,
  ArrowDownToLine,
  ArrowUpFromLine,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Node } from '@xyflow/react';

import { WorkflowNodeType, WORKFLOW_NODE_SPECS, type WorkflowNodeData } from '@/features/skills/utils/graph-node-types';
import { useGraphWorkflowContext } from '@/features/skills/contexts/graph-workflow-context';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ── Icon Map ───────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
  MessageSquare,
  Sparkles,
  GitBranch,
  ArrowRightLeft,
  ArrowDownToLine,
  ArrowUpFromLine,
};

// ── Props ──────────────────────────────────────────────────────────────────

export interface GraphConfigPanelProps {
  nodes: Node<WorkflowNodeData>[];
  onUpdateNode: (id: string, data: Partial<WorkflowNodeData>) => void;
}

// ── Per-type form components ───────────────────────────────────────────────

interface TypeFormProps {
  config: Record<string, unknown>;
  onConfigChange: (key: string, value: unknown) => void;
}

function PromptForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <>
      <FormField label="Prompt Text">
        <Textarea
          placeholder="Enter the prompt to send to the LLM..."
          value={(config.promptText as string) ?? ''}
          onChange={(e) => onConfigChange('promptText', e.target.value)}
          rows={6}
          className="resize-y bg-muted/50"
        />
      </FormField>
      <FormField label="Output Variable">
        <Input
          placeholder="e.g. result"
          value={(config.outputVar as string) ?? ''}
          onChange={(e) => onConfigChange('outputVar', e.target.value)}
          className="bg-muted/50"
        />
      </FormField>
    </>
  );
}

function SkillForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <>
      <FormField label="Skill Template" hint="Skill selector coming soon">
        <Input
          placeholder="Enter skill template ID..."
          value={(config.skillTemplateId as string) ?? ''}
          onChange={(e) => onConfigChange('skillTemplateId', e.target.value)}
          className="bg-muted/50"
        />
      </FormField>
      <FormField label="Override Instructions">
        <Input
          placeholder="Additional instructions for this skill..."
          value={(config.overrideInstructions as string) ?? ''}
          onChange={(e) => onConfigChange('overrideInstructions', e.target.value)}
          className="bg-muted/50"
        />
      </FormField>
    </>
  );
}

function ConditionForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <FormField
      label="Condition Expression"
      hint='JavaScript-like expression, e.g. result.score > 0.8'
    >
      <Input
        placeholder="result.score > 0.8"
        value={(config.expression as string) ?? ''}
        onChange={(e) => onConfigChange('expression', e.target.value)}
        className="bg-muted/50"
      />
    </FormField>
  );
}

function TransformForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <FormField
      label="Transform Template"
      hint="Use {{input}} to reference incoming data"
    >
      <Textarea
        placeholder="Transform template..."
        value={(config.template as string) ?? ''}
        onChange={(e) => onConfigChange('template', e.target.value)}
        rows={6}
        className="resize-y bg-muted/50"
      />
    </FormField>
  );
}

function InputNodeForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <>
      <FormField label="Parameter Name">
        <Input
          placeholder="e.g. userQuery"
          value={(config.paramName as string) ?? ''}
          onChange={(e) => onConfigChange('paramName', e.target.value)}
          className="bg-muted/50"
        />
      </FormField>
      <FormField label="Parameter Type">
        <Select
          value={(config.paramType as string) ?? 'text'}
          onValueChange={(val) => onConfigChange('paramType', val)}
        >
          <SelectTrigger className="bg-muted/50">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text">Text</SelectItem>
            <SelectItem value="number">Number</SelectItem>
            <SelectItem value="boolean">Boolean</SelectItem>
            <SelectItem value="json">JSON</SelectItem>
          </SelectContent>
        </Select>
      </FormField>
      <FormField label="Description">
        <Textarea
          placeholder="Describe this input parameter..."
          value={(config.description as string) ?? ''}
          onChange={(e) => onConfigChange('description', e.target.value)}
          rows={3}
          className="resize-y bg-muted/50"
        />
      </FormField>
    </>
  );
}

function OutputNodeForm({ config, onConfigChange }: TypeFormProps) {
  return (
    <>
      <FormField label="Output Format">
        <Select
          value={(config.format as string) ?? 'text'}
          onValueChange={(val) => onConfigChange('format', val)}
        >
          <SelectTrigger className="bg-muted/50">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text">Text</SelectItem>
            <SelectItem value="json">JSON</SelectItem>
            <SelectItem value="markdown">Markdown</SelectItem>
          </SelectContent>
        </Select>
      </FormField>
      <FormField label="Template">
        <Textarea
          placeholder="Output template..."
          value={(config.template as string) ?? ''}
          onChange={(e) => onConfigChange('template', e.target.value)}
          rows={4}
          className="resize-y bg-muted/50"
        />
      </FormField>
    </>
  );
}

// ── Shared form field wrapper ──────────────────────────────────────────────

function FormField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
      {hint && (
        <p className="text-[11px] text-muted-foreground/70">{hint}</p>
      )}
    </div>
  );
}

// ── Type form dispatch ─────────────────────────────────────────────────────

const TYPE_FORMS: Record<WorkflowNodeType, React.FC<TypeFormProps>> = {
  [WorkflowNodeType.Prompt]: PromptForm,
  [WorkflowNodeType.Skill]: SkillForm,
  [WorkflowNodeType.Condition]: ConditionForm,
  [WorkflowNodeType.Transform]: TransformForm,
  [WorkflowNodeType.Input]: InputNodeForm,
  [WorkflowNodeType.Output]: OutputNodeForm,
};

// ── Node color map ─────────────────────────────────────────────────────────

// Derive from single source of truth — WORKFLOW_NODE_SPECS
const NODE_COLORS: Record<WorkflowNodeType, string> = Object.fromEntries(
  Object.entries(WORKFLOW_NODE_SPECS).map(([k, v]) => [k, v.color]),
) as Record<WorkflowNodeType, string>;

const NODE_ICON_NAMES: Record<WorkflowNodeType, string> = Object.fromEntries(
  Object.entries(WORKFLOW_NODE_SPECS).map(([k, v]) => [k, v.icon]),
) as Record<WorkflowNodeType, string>;

// ── Main Component (observer — safe outside ReactFlow tree) ────────────────

export const GraphConfigPanel = observer(function GraphConfigPanel({
  nodes,
  onUpdateNode,
}: GraphConfigPanelProps) {
  const { store } = useGraphWorkflowContext();
  const { selectedNodeId } = store;

  const selectedNode = selectedNodeId
    ? nodes.find((n) => n.id === selectedNodeId)
    : null;

  const onConfigChange = useCallback(
    (key: string, value: unknown) => {
      if (!selectedNode) return;
      onUpdateNode(selectedNode.id, {
        config: { ...selectedNode.data.config, [key]: value },
      });
    },
    [selectedNode, onUpdateNode]
  );

  const onLabelChange = useCallback(
    (label: string) => {
      if (!selectedNode) return;
      onUpdateNode(selectedNode.id, { label });
    },
    [selectedNode, onUpdateNode]
  );

  const onClose = useCallback(() => {
    store.selectNode(null);
  }, [store]);

  if (!selectedNode) return null;

  const { nodeType } = selectedNode.data;
  const TypeForm = TYPE_FORMS[nodeType];
  const iconName = NODE_ICON_NAMES[nodeType];
  const Icon = ICON_MAP[iconName];
  const color = NODE_COLORS[nodeType];

  return (
    <div className="w-80 border-l border-border bg-background h-full overflow-y-auto animate-in slide-in-from-right-4 duration-200">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border p-3">
        {Icon && (
          <div
            className="flex h-7 w-7 items-center justify-center rounded-md"
            style={{ backgroundColor: `${color}20` }}
          >
            <Icon className="h-4 w-4" style={{ color }} />
          </div>
        )}
        <Input
          value={selectedNode.data.label}
          onChange={(e) => onLabelChange(e.target.value)}
          className="h-7 flex-1 border-none bg-transparent px-1 text-sm font-medium shadow-none focus-visible:ring-0"
        />
        <button
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Close configuration panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Type badge */}
      <div className="px-3 pt-3 pb-1">
        <span
          className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {nodeType.charAt(0).toUpperCase() + nodeType.slice(1)} Node
        </span>
      </div>

      {/* Type-specific form */}
      <div className="space-y-4 p-3">
        <TypeForm config={selectedNode.data.config} onConfigChange={onConfigChange} />
      </div>
    </div>
  );
});
