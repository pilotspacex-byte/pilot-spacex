/**
 * MemoryBulkActionBar — Sticky bar for bulk pin/forget of selected memories.
 *
 * Phase 71: Shows selection count + Pin All / Forget All with confirmation dialog.
 */

'use client';

import { Pin, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

interface MemoryBulkActionBarProps {
  selectedCount: number;
  onPin: () => void;
  onForget: () => void;
  isPending: boolean;
}

export function MemoryBulkActionBar({
  selectedCount,
  onPin,
  onForget,
  isPending,
}: MemoryBulkActionBarProps) {
  return (
    <div
      className="sticky bottom-0 flex items-center gap-3 rounded-lg border border-border bg-background p-3 shadow-warm-sm"
      role="toolbar"
      aria-label="Bulk memory actions"
    >
      <span className="text-sm font-medium text-foreground" aria-live="polite" aria-atomic="true">
        {selectedCount} selected
      </span>

      <Button
        variant="outline"
        size="sm"
        onClick={onPin}
        disabled={isPending}
        className="gap-1"
      >
        <Pin className="h-3.5 w-3.5" />
        Pin All
      </Button>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="destructive"
            size="sm"
            disabled={isPending}
            className="gap-1"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Forget All
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Forget {selectedCount} memories?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove {selectedCount} memories from the workspace. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onForget}>
              Forget {selectedCount} memories
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
