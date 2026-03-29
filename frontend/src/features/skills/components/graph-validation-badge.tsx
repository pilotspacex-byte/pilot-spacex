'use client';

/**
 * GraphValidationBadge — Displays validation status in the graph canvas.
 *
 * Shows a green "Valid" badge when no errors, or a red error count badge
 * with an expandable popover listing all validation errors.
 *
 * Safe to use observer() here — this component is rendered via React Flow
 * Panel, NOT as a ReactFlow node view.
 */

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { CheckCircle2, AlertTriangle, XCircle, Unplug, RotateCcw, ArrowLeftRight } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useGraphWorkflowContext } from '@/features/skills/contexts/graph-workflow-context';
import type { ValidationError } from '@/features/skills/utils/graph-validation-engine';

// ── Error icon mapping ────────────────────────────────────────────────────

function ErrorIcon({ type }: { type: ValidationError['type'] }) {
  const className = 'h-3.5 w-3.5 shrink-0';
  switch (type) {
    case 'disconnected':
      return <Unplug className={className} />;
    case 'missing_input':
    case 'missing_output':
      return <AlertTriangle className={className} />;
    case 'cycle':
      return <RotateCcw className={className} />;
    case 'type_mismatch':
      return <ArrowLeftRight className={className} />;
  }
}

// ── Component ─────────────────────────────────────────────────────────────

export const GraphValidationBadge = observer(function GraphValidationBadge() {
  const { store } = useGraphWorkflowContext();
  const [open, setOpen] = useState(false);
  const errors = store.validationErrors;

  if (errors.length === 0) {
    return (
      <div className="flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1.5 text-xs text-primary backdrop-blur-sm border border-primary/20">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Valid
      </div>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className="flex items-center gap-1.5 rounded-md bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive backdrop-blur-sm border border-destructive/20 hover:bg-destructive/15 transition-colors"
          type="button"
        >
          <XCircle className="h-3.5 w-3.5" />
          {errors.length} {errors.length === 1 ? 'error' : 'errors'}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-72 p-0"
      >
        <div className="px-3 py-2 border-b">
          <p className="text-xs font-medium">Validation Errors</p>
        </div>
        <div className="max-h-48 overflow-y-auto">
          {errors.map((error, i) => (
            <div
              key={`${error.nodeId}-${error.type}-${i}`}
              className="flex items-start gap-2 px-3 py-2 border-b border-border/50 last:border-b-0"
            >
              <ErrorIcon type={error.type} />
              <span className="text-xs text-muted-foreground leading-tight">
                {error.message}
              </span>
            </div>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
});
