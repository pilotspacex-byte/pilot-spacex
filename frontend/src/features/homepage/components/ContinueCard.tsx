'use client';

/**
 * ContinueCard — v3 homepage "resume your last conversation" hero card.
 *
 * Promotes the most recent AI session into a single prominent card under the
 * hero. Clicking the card navigates to /[slug]/chat?sessionId=<id> so the
 * ChatView can rehydrate state via the existing SessionResumeMenu path.
 *
 * Props:
 *   latestSession — pre-fetched SessionSummary (null hides the card).
 *
 * Design source: .planning/design.md §Homepage Layout v3 "Continue Card".
 *   - 22px radius, 24px padding, L2 shadow
 *   - Header: Fraunces 15px, muted
 *   - Title: Fraunces 22px, 2-line clamp
 *   - Preview: Inter 14px, muted, 2-line clamp
 *   - Footer: primary "Resume →" button
 */

import { useMemo } from 'react';
import Link from 'next/link';
import { ArrowRight, Sparkles } from 'lucide-react';
import type { SessionSummary } from '@/stores/ai/types/session';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(date: Date): string {
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSecs = Math.max(0, Math.floor(diffMs / 1000));
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  if (diffDays < 7) return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function firstContextPreview(session: SessionSummary): string {
  const entry = session.contextHistory?.find(
    (c) => c.selectedText && c.selectedText.trim().length > 0
  );
  if (entry?.selectedText) return entry.selectedText;
  if (entry?.noteTitle) return `Linked note: ${entry.noteTitle}`;
  if (session.contextType && session.contextId) {
    return `Continuing on ${session.contextType} ${session.contextId.slice(0, 8)}`;
  }
  return 'Pick up the thread and keep going.';
}

// ── Component ────────────────────────────────────────────────────────────────

interface ContinueCardProps {
  latestSession: SessionSummary | null;
  workspaceSlug: string;
}

export function ContinueCard({ latestSession, workspaceSlug }: ContinueCardProps) {
  const derived = useMemo(() => {
    if (!latestSession) return null;
    return {
      title: latestSession.title?.trim() || 'Untitled conversation',
      preview: firstContextPreview(latestSession),
      timestamp: formatRelativeTime(latestSession.updatedAt),
      href: `/${workspaceSlug}/chat?sessionId=${latestSession.sessionId}`,
    };
  }, [latestSession, workspaceSlug]);

  // Empty state: prompt user to start their first chat instead of rendering nothing.
  if (!derived) {
    return (
      <section aria-label="Start a conversation">
        <Link
          href={`/${workspaceSlug}/chat`}
          className="group relative block rounded-[22px] border border-dashed border-border bg-card/50 p-6 transition-all duration-200 hover:border-border/80 hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" strokeWidth={1.75} />
            </div>
            <div className="flex-1">
              <p className="font-display text-[15px] font-normal text-muted-foreground">
                Start your first conversation
              </p>
              <h3 className="mt-1 font-display text-[22px] font-normal leading-[1.25] tracking-[-0.01em] text-foreground">
                Ask Pilot anything
              </h3>
              <p className="mt-2 text-sm leading-[1.55] text-muted-foreground">
                Draft a spec, triage issues, or summarise a note — Pilot picks up the context.
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-transform duration-150 group-hover:translate-x-[2px]">
              New chat
              <ArrowRight className="h-4 w-4" aria-hidden="true" strokeWidth={2} />
            </span>
          </div>
        </Link>
      </section>
    );
  }

  return (
    <section aria-label="Continue where you left off">
      <Link
        href={derived.href}
        className="group relative block rounded-[22px] border border-border bg-card p-6 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_8px_24px_-12px_rgb(0_0_0/0.08)] transition-all duration-200 hover:-translate-y-[2px] hover:shadow-[0_2px_4px_rgb(0_0_0/0.04),0_16px_40px_-16px_rgb(0_0_0/0.12)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        {/* Header row */}
        <div className="flex items-center justify-between">
          <p className="font-display text-[15px] font-normal text-muted-foreground">
            Continue where you left off
          </p>
          <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
            {derived.timestamp}
          </span>
        </div>

        {/* Title */}
        <h3 className="mt-3 line-clamp-2 font-display text-[22px] font-normal leading-[1.25] tracking-[-0.01em] text-foreground">
          {derived.title}
        </h3>

        {/* Preview */}
        <p className="mt-2 line-clamp-2 text-sm leading-[1.55] text-muted-foreground">
          {derived.preview}
        </p>

        {/* Footer — primary CTA */}
        <div className="mt-5 flex items-center justify-end">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-transform duration-150 group-hover:translate-x-[2px]">
            Resume
            <ArrowRight className="h-4 w-4" aria-hidden="true" strokeWidth={2} />
          </span>
        </div>
      </Link>
    </section>
  );
}
