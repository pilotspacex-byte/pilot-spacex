'use client';

/**
 * DigestSuggestionCard (H044) — Individual digest suggestion card.
 * Displays category icon, title, description, action button, and dismiss button.
 */

import { useRouter } from 'next/navigation';
import {
  Clock,
  FileWarning,
  AlertTriangle,
  GitBranch,
  UserPlus,
  CalendarClock,
  GitPullRequest,
  Copy,
  Sparkles,
  Activity,
  BookOpen,
  Package,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { DigestCategory, DigestSuggestion } from '../../types';
import { DIGEST_CATEGORY_LABELS } from '../../constants';

/**
 * Maps category string to the actual lucide-react icon component.
 * Avoids dynamic lookup — all icons are statically imported.
 */
const CATEGORY_ICON_MAP: Record<DigestCategory, React.ComponentType<{ className?: string }>> = {
  stale_issues: Clock,
  missing_docs: FileWarning,
  inconsistent_status: AlertTriangle,
  blocked_deps: GitBranch,
  unassigned_work: UserPlus,
  overdue_cycles: CalendarClock,
  pr_review_pending: GitPullRequest,
  duplicate_candidates: Copy,
  note_refinement: Sparkles,
  project_health: Activity,
  knowledge_gaps: BookOpen,
  release_readiness: Package,
};

interface DigestSuggestionCardProps {
  suggestion: DigestSuggestion;
  onDismiss: (suggestion: DigestSuggestion) => void;
}

export function DigestSuggestionCard({ suggestion, onDismiss }: DigestSuggestionCardProps) {
  const router = useRouter();
  const Icon = CATEGORY_ICON_MAP[suggestion.category] ?? Activity;

  const handleAction = () => {
    if (suggestion.action_url) {
      router.push(suggestion.action_url);
    }
  };

  return (
    <div
      role="article"
      aria-label={`${DIGEST_CATEGORY_LABELS[suggestion.category] ?? suggestion.category}: ${suggestion.title}. ${suggestion.description}`}
      className={cn(
        'group flex gap-3 rounded-md bg-background-subtle p-3',
        'motion-safe:transition-colors motion-safe:duration-150',
        'hover:bg-background-muted'
      )}
    >
      {/* Category icon */}
      <div className="mt-0.5 shrink-0">
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{suggestion.title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
          {suggestion.description}
        </p>

        {/* Entity reference */}
        {suggestion.entity_identifier && (
          <p className="mt-1 text-xs text-muted-foreground">
            {suggestion.entity_identifier}
            {suggestion.project_name && (
              <span className="text-muted-foreground"> · {suggestion.project_name}</span>
            )}
          </p>
        )}

        {/* Action button */}
        {suggestion.action_url && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAction}
            className="mt-1.5 h-7 px-2 text-xs text-primary"
          >
            {suggestion.action_label ?? 'View'}
          </Button>
        )}
      </div>

      {/* Dismiss button (H-6: 44px min touch target for WCAG 2.2) */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onDismiss(suggestion)}
        aria-label="Dismiss suggestion"
        className={cn(
          'min-h-[44px] min-w-[44px] shrink-0 text-muted-foreground opacity-0',
          'group-hover:opacity-100',
          'focus-visible:opacity-100',
          'motion-safe:transition-opacity'
        )}
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
