'use client';

/**
 * ImplementIssueButton — One-click Implement button for the issue detail page.
 *
 * Tauri-only: renders only when isTauri() returns true.
 *
 * Clicking the button:
 *   1. Opens a progress dialog showing pipeline steps
 *   2. Triggers ImplementStore.startImplement() (branch -> pilot implement -> stage -> commit -> push)
 *   3. Opens the terminal panel so user can see sidecar output
 *
 * The dialog shows:
 *   - Step indicator with icons (branching, implementing, staging, committing, pushing, done, error)
 *   - Scrollable output area with the last 20 lines of sidecar output
 *   - Error box on failure with clear message
 *   - Success box on completion with commit OID
 *   - Cancel button (only during 'implementing' step)
 *   - Close button (only when done or error)
 */

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { Play, Loader2, CheckCircle2, XCircle, GitBranch, Square } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

import { useImplementStore, useTerminalStore, useProjectStore } from '@/stores/RootStore';
import type { ImplementStep } from '@/stores/features/implement/ImplementStore';

export interface ImplementIssueButtonProps {
  /** The issue identifier (e.g., "PS-42"). */
  issueId: string;
  /** Optional: absolute path to the repository. Falls back to the first project in ProjectStore. */
  repoPath?: string;
}

/** Map each pipeline step to a status badge variant and icon. */
function StepIcon({ step }: { step: ImplementStep }) {
  const spinning = ['branching', 'implementing', 'staging', 'committing', 'pushing'].includes(step);
  if (step === 'done') {
    return <CheckCircle2 className="size-4 shrink-0 text-green-500" />;
  }
  if (step === 'error') {
    return <XCircle className="size-4 shrink-0 text-destructive" />;
  }
  if (step === 'branching') {
    return <GitBranch className="size-4 shrink-0 animate-pulse text-muted-foreground" />;
  }
  if (spinning) {
    return <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />;
  }
  return null;
}

/** Badge variant for the current step. */
function stepBadgeVariant(
  step: ImplementStep
): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (step === 'done') return 'default';
  if (step === 'error') return 'destructive';
  if (step === 'idle') return 'outline';
  return 'secondary';
}

export const ImplementIssueButton = observer(function ImplementIssueButton({
  issueId,
  repoPath: repoPathProp,
}: ImplementIssueButtonProps) {
  const implementStore = useImplementStore();
  const terminalStore = useTerminalStore();
  const projectStore = useProjectStore();

  const [dialogOpen, setDialogOpen] = useState(false);

  // Determine effective repo path
  const repoPath = repoPathProp ?? projectStore.projects[0]?.path ?? null;

  const handleImplementClick = () => {
    if (!repoPath) return;
    setDialogOpen(true);
    // Open terminal panel so user can see any background sidecar output
    terminalStore.open();
    void implementStore.startImplement(issueId, repoPath);
  };

  const handleCancel = () => {
    void implementStore.cancel();
  };

  const handleClose = () => {
    setDialogOpen(false);
    implementStore.reset();
  };

  const { currentStep, stepLabel, isRunning, canCancel, output, error, commitOid, branchName } =
    implementStore;

  const isDone = currentStep === 'done';
  const isError = currentStep === 'error';
  const canClose = isDone || isError;

  // Show last 20 lines of output
  const visibleOutput = output.slice(-20);

  return (
    <>
      {/* Trigger button */}
      {repoPath ? (
        <Button
          size="sm"
          variant="default"
          onClick={handleImplementClick}
          disabled={isRunning}
          className="gap-1.5 shrink-0"
          aria-label={isRunning ? 'Running implement pipeline...' : 'One-click implement'}
        >
          {isRunning ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Play className="size-3.5" />
          )}
          Implement
        </Button>
      ) : (
        <Button
          size="sm"
          variant="outline"
          disabled
          className="gap-1.5 shrink-0"
          title="No project linked — clone or link a repository first"
          aria-label="No project linked"
        >
          <Play className="size-3.5 opacity-50" />
          Implement
        </Button>
      )}

      {/* Progress dialog */}
      <Dialog open={dialogOpen} onOpenChange={(open) => !open && canClose && handleClose()}>
        <DialogContent className="sm:max-w-md" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle className="font-mono text-base">
              Implementing <span className="text-muted-foreground font-semibold">{issueId}</span>
            </DialogTitle>
            {branchName && (
              <DialogDescription className="font-mono text-xs">
                Branch: {branchName}
              </DialogDescription>
            )}
          </DialogHeader>

          {/* Step indicator */}
          <div className="flex items-center gap-2 py-1">
            <StepIcon step={currentStep} />
            <Badge variant={stepBadgeVariant(currentStep)} className="text-xs">
              {stepLabel}
            </Badge>
          </div>

          {/* Sidecar output area */}
          {visibleOutput.length > 0 && (
            <div className="max-h-60 overflow-y-auto rounded-md bg-muted p-3 font-mono text-xs leading-relaxed">
              {visibleOutput.map((line, i) => (
                <div key={i} className="whitespace-pre-wrap break-all">
                  {line}
                </div>
              ))}
            </div>
          )}

          {/* Error box */}
          {isError && error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2">
              <p className="text-destructive text-sm font-medium">Pipeline failed</p>
              <p className="text-destructive/80 mt-0.5 text-xs font-mono break-all">{error}</p>
            </div>
          )}

          {/* Success box */}
          {isDone && (
            <div className="rounded-md border border-green-500/30 bg-green-500/10 px-3 py-2">
              <p className="text-green-700 dark:text-green-400 text-sm font-medium">
                Implementation complete
              </p>
              {commitOid && (
                <p className="text-green-600/80 dark:text-green-400/70 mt-0.5 font-mono text-xs break-all">
                  Commit: {commitOid}
                </p>
              )}
            </div>
          )}

          {/* Action row */}
          <div className="flex justify-end gap-2 pt-1">
            {canCancel && (
              <Button variant="outline" size="sm" onClick={handleCancel} className="gap-1.5">
                <Square className="size-3.5" />
                Cancel
              </Button>
            )}
            {canClose && (
              <Button variant="default" size="sm" onClick={handleClose}>
                Close
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});
