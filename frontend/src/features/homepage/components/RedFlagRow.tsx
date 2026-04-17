'use client';

/**
 * RedFlagRow — v3 homepage "what's on fire" chip row.
 *
 * Consumes useWorkspaceDigest categories and surfaces up to 4 priority chips
 * (stale / cycle / blocked / overdue / unassigned / unlinked). Each chip is a
 * button linking to a filtered list route. When the digest is empty we render
 * an "All clear" calm state to preserve vertical rhythm.
 *
 * Ordering priority (most urgent first):
 *   1. blocked_dependencies
 *   2. overdue_items
 *   3. stale_issues
 *   4. cycle_risk
 *   5. unassigned_priority
 *   6. unlinked_notes
 *
 * Design source: .planning/design.md §Homepage Layout v3 "Red Flag Row".
 */

import { useMemo } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Clock,
  FileText,
  Folder,
  Link2Off,
  Sparkles,
  UserX,
  type LucideIcon,
} from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { useWorkspaceStore } from '@/stores/RootStore';
import type { DigestCategory } from '../types';
import { useWorkspaceDigest } from '../hooks/useWorkspaceDigest';

// ── Chip spec ────────────────────────────────────────────────────────────────

interface RedFlagChip {
  id: DigestCategory | 'cycle_risk_single';
  icon: LucideIcon;
  label: string;
  href: string;
  ariaLabel: string;
  accent: 'amber' | 'red' | 'orange' | 'blue' | 'slate';
}

/** Lower rank = higher urgency. */
const CATEGORY_PRIORITY: Record<DigestCategory, number> = {
  blocked_dependencies: 1,
  overdue_items: 2,
  stale_issues: 3,
  cycle_risk: 4,
  unassigned_priority: 5,
  unlinked_notes: 6,
};

const ACCENT_CLASSES: Record<RedFlagChip['accent'], string> = {
  red: 'text-red-600 dark:text-red-400',
  amber: 'text-amber-600 dark:text-amber-400',
  orange: 'text-orange-600 dark:text-orange-400',
  blue: 'text-blue-600 dark:text-blue-400',
  slate: 'text-muted-foreground',
};

const MAX_CHIPS = 4;

// ── Helpers ──────────────────────────────────────────────────────────────────

function plural(count: number, singular: string, pluralWord?: string): string {
  return count === 1 ? singular : (pluralWord ?? `${singular}s`);
}

function buildChip(
  category: DigestCategory,
  count: number,
  workspaceSlug: string
): RedFlagChip | null {
  if (count <= 0) return null;

  switch (category) {
    case 'blocked_dependencies':
      return {
        id: category,
        icon: Link2Off,
        label: `${count} blocked ${plural(count, 'item')}`,
        href: `/${workspaceSlug}/issues?blocked=true`,
        ariaLabel: `${count} blocked ${plural(count, 'item')} — open filtered list`,
        accent: 'red',
      };
    case 'overdue_items':
      return {
        id: category,
        icon: Clock,
        label: `${count} overdue ${plural(count, 'item')}`,
        href: `/${workspaceSlug}/issues?overdue=true`,
        ariaLabel: `${count} overdue ${plural(count, 'item')} — open filtered list`,
        accent: 'orange',
      };
    case 'stale_issues':
      return {
        id: category,
        icon: AlertTriangle,
        label: `${count} stale ${plural(count, 'issue')}`,
        href: `/${workspaceSlug}/issues?stale=true`,
        ariaLabel: `${count} stale ${plural(count, 'issue')} — open filtered list`,
        accent: 'amber',
      };
    case 'cycle_risk':
      return {
        id: 'cycle_risk_single',
        icon: Clock,
        label: count === 1 ? 'Cycle at risk' : `${count} cycles at risk`,
        href: `/${workspaceSlug}/dashboard`,
        ariaLabel:
          count === 1
            ? 'Cycle at risk — open dashboard'
            : `${count} cycles at risk — open dashboard`,
        accent: 'orange',
      };
    case 'unassigned_priority':
      return {
        id: category,
        icon: UserX,
        label: `${count} unassigned ${plural(count, 'priority', 'priorities')}`,
        href: `/${workspaceSlug}/issues?unassigned=true`,
        ariaLabel: `${count} unassigned ${plural(count, 'priority item', 'priority items')} — open filtered list`,
        accent: 'amber',
      };
    case 'unlinked_notes':
      return {
        id: category,
        icon: Sparkles,
        label: `${count} unlinked ${plural(count, 'note')}`,
        href: `/${workspaceSlug}/notes?unlinked=true`,
        ariaLabel: `${count} unlinked ${plural(count, 'note')} — open filtered list`,
        accent: 'blue',
      };
    default:
      return null;
  }
}

// ── Component ────────────────────────────────────────────────────────────────

interface RedFlagRowProps {
  workspaceSlug: string;
  workspaceId: string;
}

export const RedFlagRow = observer(function RedFlagRow({
  workspaceSlug,
  workspaceId,
}: RedFlagRowProps) {
  const workspaceStore = useWorkspaceStore();
  const { groups, isLoading } = useWorkspaceDigest({
    workspaceId,
    enabled: !!workspaceId,
  });

  const chips = useMemo<RedFlagChip[]>(() => {
    if (groups.length === 0) return [];

    const sorted = [...groups].sort(
      (a, b) => CATEGORY_PRIORITY[a.category] - CATEGORY_PRIORITY[b.category]
    );

    const built: RedFlagChip[] = [];
    for (const group of sorted) {
      const chip = buildChip(group.category, group.items.length, workspaceSlug);
      if (chip) built.push(chip);
      if (built.length >= MAX_CHIPS) break;
    }
    return built;
  }, [groups, workspaceSlug]);

  // Don't render a skeleton — the row is non-essential and we avoid CLS.
  if (isLoading) return null;

  // Zero digest fallback: surface real workspace stats so the row is never truly empty.
  if (chips.length === 0) {
    const ws = workspaceStore.currentWorkspace as
      | (typeof workspaceStore.currentWorkspace & { projectCount?: number })
      | null;
    const projectCount = ws?.projectCount ?? 0;
    const memberCount = ws?.memberCount ?? 0;
    const fallbackChips: RedFlagChip[] = [];

    if (projectCount > 0) {
      fallbackChips.push({
        id: 'unlinked_notes',
        icon: Folder,
        label: `${projectCount} ${plural(projectCount, 'project')}`,
        href: `/${workspaceSlug}/projects`,
        ariaLabel: `${projectCount} ${plural(projectCount, 'project')} — open projects`,
        accent: 'slate',
      });
    }
    fallbackChips.push({
      id: 'stale_issues',
      icon: CircleDot,
      label: 'All issues',
      href: `/${workspaceSlug}/issues`,
      ariaLabel: 'Browse all issues',
      accent: 'blue',
    });
    fallbackChips.push({
      id: 'unlinked_notes',
      icon: FileText,
      label: 'All notes',
      href: `/${workspaceSlug}/notes`,
      ariaLabel: 'Browse all notes',
      accent: 'slate',
    });
    if (memberCount > 1) {
      fallbackChips.push({
        id: 'unassigned_priority',
        icon: UserX,
        label: `${memberCount} ${plural(memberCount, 'member')}`,
        href: `/${workspaceSlug}/members`,
        ariaLabel: `${memberCount} ${plural(memberCount, 'member')} — open members`,
        accent: 'slate',
      });
    }

    return (
      <section
        aria-label="Workspace shortcuts"
        className="-mx-6 overflow-x-auto px-6 py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/40 px-3 py-1.5 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
            <span>All clear</span>
          </span>
          <ul className="flex snap-x snap-mandatory gap-2">
            {fallbackChips.map((chip, i) => {
              const Icon = chip.icon;
              return (
                <li key={`${chip.id}-${i}`} className="snap-start">
                  <Link
                    href={chip.href}
                    aria-label={chip.ariaLabel}
                    className="group inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-[0_1px_0_rgb(0_0_0/0.02)] transition-all duration-150 hover:-translate-y-[1px] hover:border-border/80 hover:shadow-[0_2px_8px_rgb(0_0_0/0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <Icon
                      className={`h-3.5 w-3.5 shrink-0 ${ACCENT_CLASSES[chip.accent]}`}
                      aria-hidden="true"
                      strokeWidth={2}
                    />
                    <span className="whitespace-nowrap underline-offset-4 group-hover:underline">
                      {chip.label}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Workspace red flags"
      className="-mx-6 overflow-x-auto px-6 py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      <ul
        className="flex snap-x snap-mandatory gap-2"
        style={{ scrollPaddingInlineStart: '1.5rem' }}
      >
        {chips.map((chip) => {
          const Icon = chip.icon;
          return (
            <li key={chip.id} className="snap-start">
              <Link
                href={chip.href}
                aria-label={chip.ariaLabel}
                className="group inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-[0_1px_0_rgb(0_0_0/0.02)] transition-all duration-150 hover:-translate-y-[1px] hover:border-border/80 hover:shadow-[0_2px_8px_rgb(0_0_0/0.06)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <Icon
                  className={`h-3.5 w-3.5 shrink-0 ${ACCENT_CLASSES[chip.accent]}`}
                  aria-hidden="true"
                  strokeWidth={2}
                />
                <span className="whitespace-nowrap underline-offset-4 group-hover:underline">
                  {chip.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
});
