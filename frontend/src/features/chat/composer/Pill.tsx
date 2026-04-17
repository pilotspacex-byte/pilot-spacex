/**
 * Pill — base visual container shared by all composer toolbar pills.
 *
 * v3 Gemini-style composer: rounded-full bordered chips on the chatbox surface
 * (`--surface-chatbox`). Each concrete pill (AgentPill, SkillPill, etc.) composes
 * this component to get consistent padding/typography/hover state.
 *
 * Keep this component visual-only — no state, no popovers — so wrapper pills
 * can forward refs and `asChild` semantics to Radix PopoverTrigger cleanly.
 */

import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface PillProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Leading icon (typically a lucide-react icon element) */
  icon?: ReactNode;
  /** Short label shown next to the icon */
  label?: string;
  /** Optional trailing element (chevron, count badge, etc.) */
  trailing?: ReactNode;
  /** Visual active/selected state — stronger border/bg */
  active?: boolean;
  /** When true, renders as a square icon-only button (36x36) instead of pill-shaped */
  iconOnly?: boolean;
}

export const Pill = forwardRef<HTMLButtonElement, PillProps>(
  ({ icon, label, trailing, active, iconOnly, className, children, ...rest }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        {...rest}
        className={cn(
          'inline-flex items-center gap-1.5 text-xs font-medium',
          'border border-[var(--border-toolbar)] bg-card text-foreground',
          'transition-colors duration-150',
          'hover:bg-accent hover:text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-1',
          'disabled:pointer-events-none disabled:opacity-50',
          iconOnly
            ? 'h-8 w-8 justify-center rounded-full'
            : 'h-8 rounded-full px-3 py-1.5',
          active && 'bg-accent text-accent-foreground border-foreground/40',
          className
        )}
      >
        {icon}
        {!iconOnly && label && <span>{label}</span>}
        {!iconOnly && trailing}
        {children}
      </button>
    );
  }
);

Pill.displayName = 'Pill';
