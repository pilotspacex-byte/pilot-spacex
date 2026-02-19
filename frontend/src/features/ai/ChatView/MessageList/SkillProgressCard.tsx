/**
 * SkillProgressCard — renders active/completed skill execution in the chat timeline.
 *
 * States: queued → running (animated progress) → completed / failed
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §2
 * T-053
 */
'use client';

import { memo, useCallback } from 'react';
import { Cpu, CheckCircle, AlertTriangle, Clock, ExternalLink, RefreshCw, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

interface SkillProgressCardProps {
  intent: WorkIntentState;
  onViewArtifact?: (artifactId: string, artifactType: string) => void;
  onRevise?: (intentId: string) => void;
  onDismiss?: (intentId: string) => void;
  className?: string;
}

function StatusBadge({ status }: { status: WorkIntentState['status'] }) {
  if (status === 'executing') {
    return (
      <Badge variant="secondary" className="bg-ai/15 text-ai border-0 gap-1.5 text-xs font-medium">
        <span
          className="h-1.5 w-1.5 rounded-full bg-ai animate-pulse inline-block"
          aria-hidden="true"
        />
        Running…
      </Badge>
    );
  }
  if (status === 'completed') {
    return (
      <Badge
        variant="default"
        className="bg-primary/15 text-primary border-0 gap-1.5 text-xs font-medium"
      >
        <CheckCircle className="h-3 w-3" aria-hidden="true" />
        Complete
      </Badge>
    );
  }
  if (status === 'failed') {
    return (
      <Badge variant="destructive" className="gap-1.5 text-xs font-medium">
        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
        Failed
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1.5 text-xs font-medium">
      <Clock className="h-3 w-3" aria-hidden="true" />
      Queued
    </Badge>
  );
}

function ProgressBar({
  progress,
  step,
  totalSteps,
}: {
  progress: number;
  step?: number;
  totalSteps?: number;
}) {
  const hasCounts = step !== undefined && totalSteps !== undefined && totalSteps > 0;
  return (
    <div className="space-y-1">
      <div
        className="h-1 rounded-full bg-border overflow-hidden"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={hasCounts ? `Step ${step} of ${totalSteps}` : `${progress}%`}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] linear duration-300"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      {hasCounts && (
        <p className="text-xs text-muted-foreground tabular-nums">
          Step {step}/{totalSteps}
        </p>
      )}
    </div>
  );
}

export const SkillProgressCard = memo<SkillProgressCardProps>(function SkillProgressCard({
  intent,
  onViewArtifact,
  onRevise,
  onDismiss,
  className,
}) {
  const handleRevise = useCallback(() => {
    onRevise?.(intent.intentId);
  }, [intent.intentId, onRevise]);

  const handleDismiss = useCallback(() => {
    onDismiss?.(intent.intentId);
  }, [intent.intentId, onDismiss]);

  const isRunning = intent.status === 'executing';
  const isCompleted = intent.status === 'completed';
  const isFailed = intent.status === 'failed';

  const icon = isCompleted ? (
    <CheckCircle className="h-4 w-4 text-primary" aria-hidden="true" />
  ) : isFailed ? (
    <AlertTriangle className="h-4 w-4 text-destructive" aria-hidden="true" />
  ) : (
    <Cpu className="h-4 w-4 text-ai" aria-hidden="true" />
  );

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`Skill execution: ${intent.skillName ?? 'unknown'}`}
      className={cn('mx-4 my-3 rounded-[14px] border bg-background p-4 animate-fade-up', className)}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {icon}
          <span className="text-sm font-medium font-mono truncate">
            {intent.skillName ?? 'Skill'}
          </span>
        </div>
        <StatusBadge status={intent.status} />
      </div>

      {/* Intent summary */}
      {intent.intentSummary && (
        <p className="text-sm text-muted-foreground truncate mb-3" title={intent.intentSummary}>
          {intent.intentSummary}
        </p>
      )}

      {/* Progress (only during execution) */}
      {isRunning && (
        <div className="mb-3">
          <ProgressBar
            progress={intent.skillProgress ?? 0}
            step={intent.skillStep}
            totalSteps={intent.skillTotalSteps}
          />
          {intent.skillCurrentStep && (
            <p className="text-xs text-muted-foreground mt-1">{intent.skillCurrentStep}</p>
          )}
        </div>
      )}

      {/* Error message */}
      {isFailed && intent.errorMessage && (
        <p className="text-sm text-destructive mb-3">{intent.errorMessage}</p>
      )}

      {/* Artifacts */}
      {intent.artifacts && intent.artifacts.length > 0 && (
        <div className="mb-3">
          <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1.5">Artifacts</p>
          <ul className="space-y-1">
            {intent.artifacts.map((artifact) => (
              <li key={artifact.id}>
                <button
                  type="button"
                  onClick={() => onViewArtifact?.(artifact.id, artifact.type)}
                  className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                  aria-label={`View ${artifact.name}`}
                >
                  <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                  {artifact.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Completion actions */}
      {(isCompleted || isFailed) && (
        <div className="flex items-center gap-2 mt-2">
          {isCompleted && intent.artifacts?.[0] && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const a = intent.artifacts?.[0];
                if (a) onViewArtifact?.(a.id, a.type);
              }}
              className="gap-1.5 text-xs"
            >
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
              View in Note
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={handleRevise}
            className="gap-1.5 text-xs text-ai hover:text-ai/80"
          >
            <RefreshCw className="h-3 w-3" aria-hidden="true" />
            Revise
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDismiss}
            className="gap-1.5 text-xs text-muted-foreground"
          >
            <X className="h-3 w-3" aria-hidden="true" />
            Dismiss
          </Button>
        </div>
      )}
    </div>
  );
});
