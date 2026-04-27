'use client';

/**
 * ContinueCard — Phase 88 Plan 04 Task 2 (E-02 empty-state revision).
 *
 * Single rich card on the launchpad linking to the user's most-recently
 * active chat session. When there is no prior session OR while the hook
 * is loading, we now render a 96px dashed-border placeholder explaining
 * what this surface is for — preserves vertical rhythm and gives new
 * users a clear "this is where your chats land next time" hint.
 *
 * Composition: useLastChatSession hook → null OR LastChatSession.
 *
 * Visual contract (UI-SPEC §6):
 *   • 96px fixed height
 *   • 14px (rounded-2xl ≈ 1rem; UI-SPEC says 14r → use rounded-[14px])
 *   • Section label: "CONTINUE WHERE YOU LEFT OFF" — 11px, 600, tracking-wider
 *   • Title: Inter 14/600
 *   • Preview: Inter 13/400, 1-line truncate
 *   • Timestamp: formatDistanceToNow(date, { addSuffix: true })
 *   • Up to 3 artifact pills (kind icon + label) — aria-hidden container
 *
 * Accessibility:
 *   • Outer element is an <a href> via next/link → real link (mid-click,
 *     ⌘-click, Enter, tab all behave natively).
 *   • aria-label on the link: "Continue chat: {title}, last active {timeAgo}"
 *   • Pills container is aria-hidden — the timestamp + title carry the
 *     screen-reader meaning.
 *
 * Phase 85 ArtifactCard alignment: Plan suggests preferring the compact
 * ArtifactCard variant from `@/components/artifacts`. The compact card is
 * a 72px row designed for split panes — too tall for our 3-pill row. We
 * render minimal <span> chips here and document the divergence in
 * 88-04-SUMMARY.md (deferred to Phase 89 visual harmonization).
 *
 * @module features/homepage/components/ContinueCard
 */

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { FileText, Hash, ScrollText } from 'lucide-react';
import { useLastChatSession } from '../hooks/use-last-chat-session';

interface ContinueCardProps {
  workspaceId: string;
  workspaceSlug: string;
}

/** Resolve a small icon for an artifact kind. Falls back to Hash. */
function pillIconFor(kind: string) {
  switch (kind) {
    case 'ISSUE':
      return Hash;
    case 'NOTE':
      return FileText;
    case 'SPEC':
      return ScrollText;
    default:
      return Hash;
  }
}

/**
 * Empty-state placeholder (E-02 Path B).
 *
 * Preserves the populated card's 96px height + 14px squircle radius so
 * the launchpad layout stays stable when the first chat session arrives.
 * Visual rules:
 *   • Dashed 1px border in muted neutral (vs. solid border-neutral-200
 *     when populated) — telegraphs "skeletal hint" without competing
 *     with the active surfaces above.
 *   • text-secondary muted color, no buttons, no pills.
 *   • role="status" so SRs read the explanatory copy instead of the
 *     populated card's link text.
 *   • workspaceSlug is unused for now but kept in props so future iterations
 *     can add a "Start a chat" CTA without an API change.
 */
function EmptyPlaceholder() {
  return (
    <div
      data-testid="continue-card-empty"
      role="status"
      aria-live="polite"
      className="
        block h-24 w-full rounded-[14px] border border-dashed border-neutral-200
        bg-transparent px-5 py-4
        animate-in fade-in duration-200 motion-reduce:animate-none
      "
    >
      <div className="flex h-full flex-col justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
          Continue where you left off
        </div>
        <div className="min-w-0 flex-1 pt-1">
          <div className="truncate text-[14px] font-semibold text-neutral-700">
            Your first chat will land here
          </div>
          <div className="truncate text-[13px] font-normal text-neutral-500">
            Start a topic above and you&rsquo;ll be able to pick it up next time.
          </div>
        </div>
      </div>
    </div>
  );
}

export function ContinueCard({ workspaceId, workspaceSlug }: ContinueCardProps) {
  const { session, isLoading } = useLastChatSession(workspaceId);

  // No session OR loading → render the calm placeholder so launchpad
  // rhythm holds and users understand what this surface is for once a
  // chat session exists. (E-02 Path B — replaces the prior `return null`.)
  if (!session || isLoading) {
    return <EmptyPlaceholder />;
  }

  const href = `/${workspaceSlug}/chat?session=${session.id}`;
  let timeAgo: string;
  try {
    timeAgo = formatDistanceToNow(new Date(session.lastMessageAt), { addSuffix: true });
  } catch {
    timeAgo = 'recently';
  }
  const ariaLabel = `Continue chat: ${session.title}, last active ${timeAgo}`;
  const pills = session.artifacts.slice(0, 3);

  return (
    <Link
      href={href}
      aria-label={ariaLabel}
      className="
        block h-24 w-full rounded-[14px] border border-neutral-200 bg-white px-5 py-4
        transition-colors hover:bg-neutral-50
        motion-reduce:transition-none
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400
      "
    >
      <div className="flex h-full flex-col justify-between">
        {/* Section label */}
        <div className="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
          Continue where you left off
        </div>

        {/* Title + preview row */}
        <div className="min-w-0 flex-1 pt-1">
          <div className="truncate text-[14px] font-semibold text-neutral-900">
            {session.title}
          </div>
          {session.lastMessagePreview && (
            <div className="truncate text-[13px] font-normal text-neutral-600">
              {session.lastMessagePreview}
            </div>
          )}
        </div>

        {/* Timestamp + pills row */}
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] font-normal text-neutral-500">{timeAgo}</span>

          {pills.length > 0 && (
            <div
              data-testid="continue-card-pills"
              aria-hidden="true"
              className="flex items-center gap-1.5"
            >
              {pills.map((p) => {
                const Icon = pillIconFor(p.kind);
                return (
                  <span
                    key={p.id}
                    className="
                      inline-flex items-center gap-1 rounded-md border border-neutral-200
                      bg-neutral-50 px-1.5 py-0.5 text-[11px] font-medium text-neutral-700
                    "
                  >
                    <Icon className="h-3 w-3" aria-hidden="true" />
                    <span className="max-w-[120px] truncate">{p.label}</span>
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
