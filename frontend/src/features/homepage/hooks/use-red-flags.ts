'use client';

/**
 * useRedFlags — compose RedFlag[] for the launchpad RedFlagStrip.
 *
 * Phase 88 Plan 03. Reads the existing homepage activity + digest queries and
 * derives at most 3 flags ordered stale → sprint → digest.
 *
 * Truth sources (locked decision 2026-04-24):
 *  - The activity payload exposes neither `staleCount` nor a sprint health
 *    field. The digest endpoint already classifies suggestions by
 *    DigestCategory, so it is the single source of truth for all three
 *    signals on the launchpad:
 *      • category 'stale_issues' → stale flag (count = #items)
 *      • category 'cycle_risk'   → sprint flag (uses suggestion.title)
 *      • everything else         → digest flag (highest relevanceScore)
 *
 *  - useHomepageActivity is still composed so the strip's loading/error
 *    states track both queries (per must_haves.key_links). Its `data` is
 *    intentionally unused today; if backend later adds a stale/sprint hint
 *    to the activity payload, swap the digest-derived branches here.
 *    TODO(88+): consume activity payload once backend exposes
 *    activeCycle.healthStatus or top-level staleCount.
 */

import { useMemo } from 'react';
import { useHomepageActivity } from './useHomepageActivity';
import { useWorkspaceDigest } from './useWorkspaceDigest';
import type { DigestSuggestion } from '../types';

export type RedFlagKind = 'stale' | 'sprint' | 'digest';

export interface RedFlag {
  kind: RedFlagKind;
  label: string;
  /**
   * Secondary meta line under the label (Pencil "Needs your eyes" pattern).
   * Optional — rows fall back to a single-line layout when absent.
   */
  sublabel?: string;
  /**
   * Per-row action chip text. Defaults to "Open" in the renderer when absent.
   */
  actionLabel?: string;
  href: string;
  ariaLabel: string;
}

export interface UseRedFlagsOptions {
  workspaceId: string;
  workspaceSlug: string;
}

export interface UseRedFlagsResult {
  flags: RedFlag[];
  isLoading: boolean;
  isError: boolean;
}

/**
 * `${count} stale task` / `${count} stale tasks` based on count.
 * Pluralization is locale-naive on purpose — the launchpad strip is one line.
 */
function staleLabel(count: number): string {
  return count === 1 ? '1 stale task' : `${count} stale tasks`;
}

/**
 * Pick the digest suggestion to surface as the "digest" flag.
 * Excludes stale_issues + cycle_risk (those produce dedicated flags).
 * Returns the highest-relevance remaining suggestion or null.
 */
function pickDigestSuggestion(
  suggestions: readonly DigestSuggestion[],
): DigestSuggestion | null {
  let best: DigestSuggestion | null = null;
  for (const s of suggestions) {
    if (s.category === 'stale_issues' || s.category === 'cycle_risk') continue;
    if (!best || s.relevanceScore > best.relevanceScore) {
      best = s;
    }
  }
  return best;
}

/**
 * Pick a single cycle_risk suggestion to surface as the "sprint" flag.
 * Returns the highest-relevance one or null.
 */
function pickSprintSuggestion(
  suggestions: readonly DigestSuggestion[],
): DigestSuggestion | null {
  let best: DigestSuggestion | null = null;
  for (const s of suggestions) {
    if (s.category !== 'cycle_risk') continue;
    if (!best || s.relevanceScore > best.relevanceScore) {
      best = s;
    }
  }
  return best;
}

export function useRedFlags({
  workspaceId,
  workspaceSlug,
}: UseRedFlagsOptions): UseRedFlagsResult {
  const activity = useHomepageActivity({ workspaceId });
  const digest = useWorkspaceDigest({ workspaceId });

  return useMemo<UseRedFlagsResult>(() => {
    const isLoading = activity.isLoading || digest.isLoading;
    const isError = activity.isError || digest.isError;

    // On digest error, render no flags (silent fail per UI-SPEC §4 error row).
    // The strip itself returns null when flags is empty.
    if (digest.isError) {
      return { flags: [], isLoading, isError };
    }

    const suggestions = digest.suggestions;
    const flags: RedFlag[] = [];

    // 1. Stale tasks
    const staleSuggestions = suggestions.filter((s) => s.category === 'stale_issues');
    const staleCount = staleSuggestions.length;
    if (staleCount > 0) {
      const label = staleLabel(staleCount);
      // Prefer the highest-relevance stale suggestion's description as the
      // sublabel; otherwise leave undefined and the row degrades to one line.
      const top = staleSuggestions.reduce<DigestSuggestion | null>(
        (best, s) => (!best || s.relevanceScore > best.relevanceScore ? s : best),
        null,
      );
      flags.push({
        kind: 'stale',
        label,
        sublabel: top?.description || undefined,
        actionLabel: top?.actionLabel ?? 'Review',
        href: `/${workspaceSlug}/tasks?filter=stale`,
        ariaLabel: `${label}. Open.`,
      });
    }

    // 2. Sprint health
    const sprint = pickSprintSuggestion(suggestions);
    if (sprint) {
      flags.push({
        kind: 'sprint',
        label: sprint.title,
        sublabel: sprint.description || undefined,
        actionLabel: sprint.actionLabel ?? 'Triage',
        href: `/${workspaceSlug}/projects`,
        ariaLabel: `${sprint.title}. Open.`,
      });
    }

    // 3. AI digest
    const digestItem = pickDigestSuggestion(suggestions);
    if (digestItem) {
      flags.push({
        kind: 'digest',
        label: digestItem.title,
        sublabel: digestItem.description || undefined,
        actionLabel: digestItem.actionLabel ?? 'Open',
        href: `/${workspaceSlug}/digest`,
        ariaLabel: `${digestItem.title}. Open.`,
      });
    }

    // Cap at 3 — by construction we never exceed 3, but keep an explicit slice
    // so future additions cannot regress the contract.
    return { flags: flags.slice(0, 3), isLoading, isError };
  }, [
    activity.isLoading,
    activity.isError,
    digest.isLoading,
    digest.isError,
    digest.suggestions,
    workspaceSlug,
  ]);
}
