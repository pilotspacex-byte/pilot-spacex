'use client';

/**
 * RedFlagStrip — "Needs your eyes" multi-row panel for the launchpad.
 *
 * Replaces the original single-pill banner strip with the Pencil v3
 * "Needs your eyes" pattern: a labelled panel listing one signal per row.
 * Each row is a single keyboard-accessible <a href> (no nested interactive
 * elements) carrying:
 *   - severity dot (color-coded by kind, also exposed via icon for
 *     non-color discrimination)
 *   - kind icon (aria-hidden)
 *   - primary label (medium weight)
 *   - optional sublabel meta line
 *   - per-row action chip (text + chevron, aria-hidden — anchor's aria-label
 *     already conveys destination)
 *
 * Render contract:
 *   • flags = []  AND not loading                  -> 32px dashed empty placeholder
 *   • isError                                       -> render null (silent fail)
 *   • isLoading + no flags                          -> single 32px skeleton row
 *   • flags > 0                                     -> "Needs your eyes" header
 *                                                      + N rows in region landmark
 *
 * Per-kind visual contract (UI-SPEC §4):
 *   stale  -> amber-500 accent, AlertTriangle icon, amber-50 bg
 *   sprint -> rose-500  accent, Activity icon,       rose-50  bg
 *   digest -> violet-500 accent, Sparkles icon,      violet-50 bg
 *
 * Motion: 200ms fade-in; honors prefers-reduced-motion.
 */

import Link from 'next/link';
import { Activity, AlertTriangle, ChevronRight, Sparkles } from 'lucide-react';
import type { ComponentType } from 'react';
import { useRedFlags, type RedFlag, type RedFlagKind } from '../hooks/use-red-flags';

interface RedFlagStripProps {
  workspaceId: string;
  workspaceSlug: string;
}

interface KindStyle {
  Icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' }>;
  dot: string;       // severity dot bg (carries data-flag-accent)
  bg: string;        // row bg
  hoverBg: string;
  border: string;
  iconColor: string;
  actionFg: string;  // action chip text color
  actionHoverFg: string;
}

const KIND_STYLES: Record<RedFlagKind, KindStyle> = {
  stale: {
    Icon: AlertTriangle,
    dot: 'bg-amber-500',
    bg: 'bg-amber-50',
    hoverBg: 'hover:bg-amber-100',
    border: 'border-amber-100',
    iconColor: 'text-amber-500',
    actionFg: 'text-amber-700',
    actionHoverFg: 'group-hover:text-amber-900',
  },
  sprint: {
    Icon: Activity,
    dot: 'bg-rose-500',
    bg: 'bg-rose-50',
    hoverBg: 'hover:bg-rose-100',
    border: 'border-rose-100',
    iconColor: 'text-rose-500',
    actionFg: 'text-rose-700',
    actionHoverFg: 'group-hover:text-rose-900',
  },
  digest: {
    Icon: Sparkles,
    dot: 'bg-violet-500',
    bg: 'bg-violet-50',
    hoverBg: 'hover:bg-violet-100',
    border: 'border-violet-100',
    iconColor: 'text-violet-500',
    actionFg: 'text-violet-700',
    actionHoverFg: 'group-hover:text-violet-900',
  },
};

function FlagRow({ flag }: { flag: RedFlag }) {
  const style = KIND_STYLES[flag.kind];
  const { Icon } = style;
  const actionLabel = flag.actionLabel ?? 'Open';

  return (
    <Link
      href={flag.href}
      aria-label={flag.ariaLabel}
      className={[
        'group relative flex w-full items-center gap-3 overflow-hidden',
        'rounded-xl border px-4 py-3',
        'text-[13px] leading-tight',
        'text-[#1a1a2e] transition-colors duration-150',
        'motion-reduce:transition-none',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#29a386] focus-visible:ring-offset-2',
        style.bg,
        style.hoverBg,
        style.border,
      ].join(' ')}
    >
      {/* Severity dot — color-coded; carries data-flag-accent so visual
          contract assertions remain stable. */}
      <span
        data-flag-accent
        aria-hidden="true"
        className={['h-2 w-2 shrink-0 rounded-full', style.dot].join(' ')}
      />
      <Icon
        aria-hidden="true"
        className={['h-4 w-4 shrink-0', style.iconColor].join(' ')}
      />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="truncate font-medium">{flag.label}</span>
        {flag.sublabel ? (
          <span
            data-flag-sublabel
            className="truncate text-[12px] font-normal text-[#4b5563]"
          >
            {flag.sublabel}
          </span>
        ) : null}
      </div>
      <span
        data-flag-action
        aria-hidden="true"
        className={[
          'inline-flex shrink-0 items-center gap-1 text-[12px] font-medium',
          style.actionFg,
          style.actionHoverFg,
        ].join(' ')}
      >
        {actionLabel}
        <ChevronRight className="h-3 w-3" />
      </span>
    </Link>
  );
}

function SkeletonBanner() {
  return (
    <div
      data-testid="red-flag-skeleton"
      aria-hidden="true"
      className={[
        'h-8 w-full rounded-xl bg-[#f3f4f6]',
        'animate-pulse motion-reduce:animate-none',
      ].join(' ')}
    />
  );
}

/**
 * Empty-state placeholder. Maintains a 32px footprint so the launchpad
 * vertical rhythm doesn't shift when the first flag arrives.
 */
function EmptyPlaceholder() {
  return (
    <div
      data-testid="red-flag-strip-empty"
      role="status"
      aria-live="polite"
      className={[
        'flex h-8 w-full items-center justify-center',
        'rounded-xl border border-dashed border-neutral-200 bg-transparent',
        'px-4 text-[12px] font-normal text-neutral-500',
        'animate-in fade-in duration-200 motion-reduce:animate-none',
      ].join(' ')}
    >
      No flags right now — you&rsquo;re all caught up.
    </div>
  );
}

export function RedFlagStrip({ workspaceId, workspaceSlug }: RedFlagStripProps) {
  const { flags, isLoading, isError } = useRedFlags({ workspaceId, workspaceSlug });

  // Silent fail per UI-SPEC §4 error row.
  if (isError) return null;

  // Empty + idle -> render the calm placeholder so launchpad rhythm holds.
  if (!isLoading && flags.length === 0) return <EmptyPlaceholder />;

  return (
    <section
      role="region"
      aria-label="Workspace alerts"
      className={[
        'flex w-full flex-col gap-2',
        'animate-in fade-in duration-200',
        'motion-reduce:animate-none',
      ].join(' ')}
    >
      {isLoading && flags.length === 0 ? (
        <SkeletonBanner />
      ) : (
        <>
          <h2 className="px-1 text-[12px] font-medium uppercase tracking-[0.06em] text-neutral-500">
            Needs your eyes
          </h2>
          <div className="flex flex-col gap-2">
            {flags.map((flag) => (
              <FlagRow key={flag.kind} flag={flag} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
