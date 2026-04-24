/**
 * SuggestedPromptsRow — Phase 88 Plan 02 Task 3
 *
 * Static 4-chip pill row rendered below the launchpad composer per UI-SPEC §5.
 * Clicking a chip invokes `onPick(label)` — the parent (`Launchpad.tsx`) is
 * responsible for forwarding the label to `composerRef.current?.setDraft`.
 * The chip itself does NOT submit; per the calm-launchpad principle, the
 * user must press Enter (or click Send) on the composer to navigate.
 *
 * @module features/homepage/components/SuggestedPromptsRow
 */

import { cn } from '@/lib/utils';

/** Locked prompt copy — UI-SPEC §5. Order is part of the contract. */
const SUGGESTED_PROMPTS = [
  'Draft a standup for me',
  "What's at risk today?",
  'Summarize last sprint',
  'Start a new topic',
] as const;

export interface SuggestedPromptsRowProps {
  /** Invoked with the chip label (verbatim) when the user clicks a chip. */
  onPick: (text: string) => void;
}

export function SuggestedPromptsRow({ onPick }: SuggestedPromptsRowProps) {
  return (
    <div
      role="group"
      aria-label="Suggested prompts"
      className="flex flex-wrap gap-2"
    >
      {SUGGESTED_PROMPTS.map((label) => (
        <button
          key={label}
          type="button"
          aria-label={`Use prompt: ${label}`}
          onClick={() => onPick(label)}
          className={cn(
            // Pill shape (UI-SPEC §5 dimensions: h-9, px-3.5, rounded-full)
            'inline-flex h-9 items-center rounded-full border px-3.5',
            // Color tokens — neutral chip, white default, snow on hover, chip on active
            'border-border bg-background text-text-body',
            'hover:bg-[#fafafa] hover:text-foreground',
            'active:bg-muted',
            // Type — Inter 13/500
            'text-[13px] font-medium leading-none',
            // Focus ring — 2px brand.primary outset 2 (calm-launchpad standard)
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
            // Motion — bg fade 120ms hover, suppressed under reduce-motion
            'transition-colors duration-100 motion-reduce:transition-none',
            // Cursor + select
            'cursor-pointer select-none',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
