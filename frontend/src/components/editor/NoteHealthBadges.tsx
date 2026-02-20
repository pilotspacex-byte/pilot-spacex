'use client';

/**
 * NoteHealthBadges - Pill-shaped badges indicating note health status.
 *
 * Three badges:
 * - Extractable issues (orange): paragraphs with actionable verbs
 * - Clarity issues (amber): annotations needing attention
 * - Linked issues (teal): existing issue links
 *
 * Each badge click sends a prefilled prompt to AI chat.
 * Hidden when count is 0. Collapses to single chip on mobile.
 *
 * @see T024 NoteHealthBadges component
 */
import { useCallback } from 'react';
import { FileUp, AlertCircle, Link2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { NoteHealthData } from '@/hooks/useNoteHealth';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

export interface NoteHealthBadgesProps {
  /** Health data from useNoteHealth hook */
  health: NoteHealthData;
  /** PilotSpaceStore instance for sending messages */
  pilotSpaceStore: PilotSpaceStore;
  /** Callback to open chat panel */
  onOpenChat: () => void;
  /** Whether on small screen (collapse to single chip) */
  isSmallScreen?: boolean;
  /** Additional className */
  className?: string;
}

/** Shared pill base styles */
const PILL_BASE =
  'inline-flex items-center gap-1 h-5 px-2 rounded-full text-[11px] font-medium cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1';

export function NoteHealthBadges({
  health,
  pilotSpaceStore,
  onOpenChat,
  isSmallScreen = false,
  className,
}: NoteHealthBadgesProps) {
  const { extractableCount, clarityIssueCount, linkedIssues } = health;

  const totalCount = extractableCount + clarityIssueCount;
  const hasAny = extractableCount > 0 || clarityIssueCount > 0 || linkedIssues.length > 0;

  const handleBadgeClick = useCallback(
    (prompt: string) => {
      onOpenChat();
      // Small delay so chat panel opens before message sends
      setTimeout(() => {
        pilotSpaceStore.sendMessage(prompt);
      }, 100);
    },
    [pilotSpaceStore, onOpenChat]
  );

  if (!hasAny) return null;

  // Mobile: collapsed single chip
  if (isSmallScreen && totalCount > 0) {
    return (
      <div className={cn('flex items-center', className)}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className={cn(
                PILL_BASE,
                'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900/50'
              )}
              onClick={() =>
                handleBadgeClick(
                  extractableCount > 0
                    ? `Extract ${extractableCount} actionable items as issues`
                    : `Improve clarity in ${clarityIssueCount} sections`
                )
              }
            >
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              {totalCount} item{totalCount > 1 ? 's' : ''}
            </button>
          </TooltipTrigger>
          <TooltipContent>
            {extractableCount > 0 && (
              <div>
                {extractableCount} extractable issue{extractableCount > 1 ? 's' : ''}
              </div>
            )}
            {clarityIssueCount > 0 && <div>{clarityIssueCount} need clarity</div>}
          </TooltipContent>
        </Tooltip>
      </div>
    );
  }

  // Desktop: individual badges
  return (
    <div
      className={cn('flex items-center gap-1.5 flex-wrap', className)}
      data-testid="note-health-badges"
    >
      {/* Extractable issues badge */}
      {extractableCount > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className={cn(
                PILL_BASE,
                'bg-orange-100 text-orange-800',
                'dark:bg-orange-900/30 dark:text-orange-300',
                'hover:bg-orange-200 dark:hover:bg-orange-900/50'
              )}
              onClick={() =>
                handleBadgeClick(
                  `Extract ${extractableCount} actionable item${extractableCount > 1 ? 's' : ''} as issues`
                )
              }
              data-testid="badge-extractable"
            >
              <FileUp className="h-3 w-3" aria-hidden="true" />
              {extractableCount} extractable
            </button>
          </TooltipTrigger>
          <TooltipContent>Click to extract actionable items as issues</TooltipContent>
        </Tooltip>
      )}

      {/* Clarity issues badge */}
      {clarityIssueCount > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className={cn(
                PILL_BASE,
                'bg-amber-100 text-amber-800',
                'dark:bg-amber-900/30 dark:text-amber-300',
                'hover:bg-amber-200 dark:hover:bg-amber-900/50'
              )}
              onClick={() =>
                handleBadgeClick(
                  `Improve clarity in ${clarityIssueCount} section${clarityIssueCount > 1 ? 's' : ''}`
                )
              }
              data-testid="badge-clarity"
            >
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              {clarityIssueCount} need clarity
            </button>
          </TooltipTrigger>
          <TooltipContent>Click to improve clarity with AI assistance</TooltipContent>
        </Tooltip>
      )}

      {/* Linked issues badge */}
      {linkedIssues.length > 0 && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className={cn(
                PILL_BASE,
                'bg-teal-100 text-teal-800',
                'dark:bg-teal-900/30 dark:text-teal-300',
                'hover:bg-teal-200 dark:hover:bg-teal-900/50'
              )}
              onClick={() =>
                handleBadgeClick(
                  `Summarize progress on ${linkedIssues.length} linked issue${linkedIssues.length > 1 ? 's' : ''}`
                )
              }
              data-testid="badge-linked"
            >
              <Link2 className="h-3 w-3" aria-hidden="true" />
              Linked:{' '}
              {linkedIssues
                .slice(0, 3)
                .map((i) => i.identifier)
                .join(', ')}
              {linkedIssues.length > 3 && ` +${linkedIssues.length - 3}`}
            </button>
          </TooltipTrigger>
          <TooltipContent>Click to get AI summary of linked issues</TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}
