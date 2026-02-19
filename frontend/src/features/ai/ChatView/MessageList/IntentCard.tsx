/**
 * IntentCard — renders a detected WorkIntent inline in the chat MessageList.
 *
 * States: detected → confirmed (collapsed) | rejected (collapsed) | editing | executing (replaced)
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §1
 * T-052
 */
'use client';

import { memo, useCallback, useRef, useState, useEffect } from 'react';
import { Lightbulb, Check, Pencil, X, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

interface IntentCardProps {
  intent: WorkIntentState;
  onConfirm: (intentId: string) => Promise<void>;
  onDismiss: (intentId: string) => Promise<void>;
  onEdit: (
    intentId: string,
    patch: { new_what?: string; new_why?: string; new_constraints?: string[] }
  ) => Promise<void>;
  className?: string;
}

/** Confidence bar color and label based on score. */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return '#29A386'; // primary teal
  if (confidence >= 0.7) return '#D9853F'; // amber
  return '#D9534F'; // warm red
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return 'High confidence';
  if (confidence >= 0.7) return 'Medium confidence';
  return 'Low confidence — clarification needed';
}

/** Animated confidence bar. */
function ConfidenceBar({ confidence }: { confidence: number }) {
  const [width, setWidth] = useState(0);
  const pct = Math.round(confidence * 100);
  const color = getConfidenceColor(confidence);
  const label = getConfidenceLabel(confidence);

  useEffect(() => {
    // Animate from 0 to value on mount
    const timeout = setTimeout(() => setWidth(pct), 50);
    return () => clearTimeout(timeout);
  }, [pct]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span
          className="text-xs tabular-nums font-medium"
          style={{ color: color }}
          aria-hidden="true"
        >
          {pct}%
        </span>
      </div>
      <div
        className="h-1.5 rounded-full bg-border overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence: ${pct}%`}
      >
        <div
          className="h-full rounded-full transition-[width] ease-out"
          style={{
            width: `${width}%`,
            backgroundColor: color,
            transitionDuration: '600ms',
          }}
        />
      </div>
      {confidence < 0.7 && (
        <p className="text-xs italic text-[var(--ai,#6B8FAD)]">
          AI needs clarification before proceeding with this intent.
        </p>
      )}
    </div>
  );
}

export const IntentCard = memo<IntentCardProps>(function IntentCard({
  intent,
  onConfirm,
  onDismiss,
  onEdit,
  className,
}) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editWhat, setEditWhat] = useState(intent.what);
  const [editWhy, setEditWhy] = useState(intent.why ?? '');
  const [editConstraints, setEditConstraints] = useState((intent.constraints ?? []).join('\n'));
  const whatRef = useRef<HTMLTextAreaElement>(null);

  const handleConfirm = useCallback(async () => {
    setIsConfirming(true);
    try {
      await onConfirm(intent.intentId);
    } finally {
      setIsConfirming(false);
    }
  }, [intent.intentId, onConfirm]);

  const handleDismiss = useCallback(async () => {
    setIsDismissing(true);
    try {
      await onDismiss(intent.intentId);
    } finally {
      setIsDismissing(false);
    }
  }, [intent.intentId, onDismiss]);

  const handleStartEdit = useCallback(() => {
    setEditWhat(intent.what);
    setEditWhy(intent.why ?? '');
    setEditConstraints((intent.constraints ?? []).join('\n'));
    setIsEditing(true);
    requestAnimationFrame(() => whatRef.current?.focus());
  }, [intent]);

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
  }, []);

  const handleSaveEdit = useCallback(async () => {
    setIsSavingEdit(true);
    try {
      await onEdit(intent.intentId, {
        new_what: editWhat.trim() || undefined,
        new_why: editWhy.trim() || undefined,
        new_constraints: editConstraints
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setIsEditing(false);
    } finally {
      setIsSavingEdit(false);
    }
  }, [intent.intentId, editWhat, editWhy, editConstraints, onEdit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancelEdit();
      }
    },
    [handleCancelEdit]
  );

  // Confirmed collapsed state
  if (intent.status === 'confirmed') {
    return (
      <div
        role="article"
        aria-label={`Intent confirmed: ${intent.what}`}
        className={cn(
          'mx-4 my-2 flex items-center gap-2 px-4 py-2.5 rounded-[14px]',
          'border border-primary/30 bg-primary/5 animate-fade-up',
          className
        )}
      >
        <Check className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-primary truncate">
          Intent confirmed: {intent.what}
        </span>
      </div>
    );
  }

  // Rejected collapsed state
  if (intent.status === 'rejected') {
    return (
      <div
        role="article"
        aria-label={`Intent dismissed: ${intent.what}`}
        className={cn(
          'mx-4 my-2 flex items-center gap-2 px-4 py-2.5 rounded-[14px]',
          'border border-border bg-muted/30',
          className
        )}
      >
        <X className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
        <span className="text-sm text-muted-foreground line-through truncate">{intent.what}</span>
      </div>
    );
  }

  // Executing / completed — IntentCard is replaced by SkillProgressCard
  if (
    intent.status === 'executing' ||
    intent.status === 'completed' ||
    intent.status === 'failed'
  ) {
    return null;
  }

  const isLoading = isConfirming || isDismissing || isSavingEdit;

  return (
    <div
      role="article"
      aria-label={`Work intent: ${intent.what}`}
      className={cn(
        'mx-4 my-3 rounded-[14px] border p-4 animate-fade-up',
        'border-[var(--color-ai-border,hsl(var(--ai)/0.3))] bg-[var(--color-ai-bg,hsl(var(--ai)/0.06))]',
        'max-h-80 overflow-y-auto',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="h-4 w-4 text-[var(--ai,#6B8FAD)] shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-[var(--ai,#6B8FAD)]">Intent Detected</span>
      </div>

      {isEditing ? (
        /* Edit mode */
        <div className="space-y-3" onKeyDown={handleKeyDown}>
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">WHAT</p>
            <Textarea
              ref={whatRef}
              value={editWhat}
              onChange={(e) => setEditWhat(e.target.value)}
              rows={2}
              className="resize-none text-sm"
              aria-label="Intent description"
            />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">WHY</p>
            <Textarea
              value={editWhy}
              onChange={(e) => setEditWhy(e.target.value)}
              rows={2}
              className="resize-none text-sm"
              aria-label="Intent motivation"
            />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
              CONSTRAINTS (one per line)
            </p>
            <Textarea
              value={editConstraints}
              onChange={(e) => setEditConstraints(e.target.value)}
              rows={3}
              className="resize-none text-sm font-mono"
              aria-label="Intent constraints"
            />
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleSaveEdit}
              disabled={isSavingEdit}
              aria-busy={isSavingEdit}
              className="gap-1.5"
            >
              {isSavingEdit ? (
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              ) : null}
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancelEdit}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        /* Display mode */
        <>
          <div className="space-y-3 mb-3">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">WHAT</p>
              <p className="text-sm text-foreground">{intent.what}</p>
            </div>

            {intent.why && (
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">WHY</p>
                <p className="text-sm text-foreground">{intent.why}</p>
              </div>
            )}

            {intent.constraints && intent.constraints.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                  CONSTRAINTS
                </p>
                <ul className="text-sm text-muted-foreground space-y-0.5 list-disc list-inside">
                  {intent.constraints.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="mb-4">
            <ConfidenceBar confidence={intent.confidence} />
          </div>

          {/* Actions — focus order: Confirm > Edit > Dismiss */}
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={handleConfirm}
              disabled={isLoading}
              aria-busy={isConfirming}
              aria-label="Confirm intent"
              data-testid="intent-confirm"
              className="gap-1.5"
            >
              {isConfirming ? (
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
              )}
              Confirm
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleStartEdit}
              disabled={isLoading}
              aria-label="Edit intent"
              data-testid="intent-edit"
              className="gap-1.5"
            >
              <Pencil className="h-3 w-3" aria-hidden="true" />
              Edit
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleDismiss}
              disabled={isLoading}
              aria-busy={isDismissing}
              aria-label="Dismiss intent"
              data-testid="intent-dismiss"
              className="gap-1.5 text-muted-foreground hover:text-foreground"
            >
              {isDismissing ? (
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              ) : (
                <X className="h-3 w-3" aria-hidden="true" />
              )}
              Dismiss
            </Button>
          </div>
        </>
      )}
    </div>
  );
});
