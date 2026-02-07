'use client';

/**
 * DigestEmptyState (H063) — Empty state for the Digest Panel.
 * Two variants: no AI provider configured, or no suggestions available.
 */

import { Lightbulb, Settings } from 'lucide-react';
import { useWorkspaceStore } from '@/stores/RootStore';

interface DigestEmptyStateProps {
  variant: 'no-provider' | 'no-suggestions';
}

export function DigestEmptyState({ variant }: DigestEmptyStateProps) {
  const workspaceStore = useWorkspaceStore();
  const slug = workspaceStore.currentWorkspace?.slug ?? '';

  if (variant === 'no-provider') {
    return (
      <div className="flex flex-col items-center justify-center gap-3 px-4 py-8 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-background-muted">
          <Settings className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">AI not configured</p>
          <p className="text-xs text-muted-foreground">
            Configure an AI provider in{' '}
            <a
              href={`/${slug}/settings/ai-providers`}
              className="text-primary underline underline-offset-2"
            >
              Settings
            </a>{' '}
            to enable workspace insights.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 px-4 py-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-muted">
        <Lightbulb className="h-5 w-5 text-primary" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">No suggestions yet</p>
        <p className="text-xs text-muted-foreground">
          AI insights will appear here as your workspace grows.
        </p>
      </div>
    </div>
  );
}
