'use client';

/**
 * TopicBreadcrumb — Plan 93-05 Task 2.
 *
 * Renders the ancestor chain `Home › Parent › … › Current` on a topic detail
 * page. Reads `useTopicAncestors(workspaceId, noteId)` (Plan 93-03) which
 * returns root → leaf order including the topic itself.
 *
 * Interactions (UI-SPEC §Surface 2 locked copy):
 *   - Plain click on an ancestor segment → Next.js `<Link>` navigates to that
 *     ancestor's topic page.
 *   - Alt-click (or Option-click on Mac) → opens the segment in the Phase 86
 *     Peek Drawer via `?peek=<id>&peekType=NOTE` (the canonical entity-peek
 *     URL contract surfaced by `useArtifactPeekState.openPeek`).
 *   - Final segment is a non-link `<span aria-current="page">`.
 *
 * Truncation (Decision Z — static threshold of 5 ancestors for v1):
 *   When the ancestor chain has > 5 segments, the middle segments collapse
 *   into a Radix Popover triggered by a `…` button. ResizeObserver-driven
 *   width-based truncation is deferred.
 *
 * Loading: skeleton row of 3 segments. Error: inline copy "Couldn't load
 * breadcrumb." Pending or empty list: render nothing (silent no-op).
 *
 * Pitfall guarded:
 *   The ancestors endpoint returns `[root, …, self]`. We split on the LAST
 *   element which is always the current topic — never assume it's at index 0.
 */

import { Fragment } from 'react';
import Link from 'next/link';
import { ChevronRight } from 'lucide-react';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useArtifactPeekState } from '@/hooks/use-artifact-peek-state';
import { useTopicAncestors } from '../hooks';
import type { Note } from '@/types';

const STATIC_TRUNCATION_THRESHOLD = 5;

interface Props {
  workspaceId: string;
  workspaceSlug: string;
  noteId: string;
}

function ChevronSeparator() {
  return (
    <ChevronRight
      aria-hidden="true"
      className="h-3 w-3 shrink-0 text-[var(--text-muted)]"
    />
  );
}

function BreadcrumbSkeleton() {
  return (
    <nav aria-label="Breadcrumb" className="min-h-8 flex items-center gap-2 text-[13px]">
      <div className="h-3 w-12 rounded bg-[var(--surface-input)] animate-pulse" />
      <ChevronSeparator />
      <div className="h-3 w-16 rounded bg-[var(--surface-input)] animate-pulse" />
      <ChevronSeparator />
      <div className="h-3 w-20 rounded bg-[var(--surface-input)] animate-pulse" />
    </nav>
  );
}

interface SegmentLinkProps {
  workspaceSlug: string;
  ancestor: Note;
  onAltClick: (id: string) => void;
}

function SegmentLink({ workspaceSlug, ancestor, onAltClick }: SegmentLinkProps) {
  const title = ancestor.title?.trim() || 'Untitled';
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (e.altKey) {
      e.preventDefault();
      onAltClick(ancestor.id);
    }
    // Plain click — let Next.js Link navigate.
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          href={`/${workspaceSlug}/topics/${ancestor.id}`}
          onClick={handleClick}
          aria-label={`${title}, parent topic`}
          className="text-[13px] font-medium text-[var(--text-heading)] motion-safe:transition-colors hover:text-[var(--brand-primary)] truncate max-w-[180px]"
        >
          {title}
        </Link>
      </TooltipTrigger>
      <TooltipContent>
        <span className="font-mono text-[10px] font-semibold">
          Click to open · ⌥-click to peek
        </span>
      </TooltipContent>
    </Tooltip>
  );
}

export function TopicBreadcrumb({ workspaceId, workspaceSlug, noteId }: Props) {
  const { data: ancestors, isLoading, isError } = useTopicAncestors(workspaceId, noteId);
  const { openPeek } = useArtifactPeekState();

  const handleAltClick = (id: string) => {
    openPeek(id, 'NOTE');
  };

  if (isLoading) return <BreadcrumbSkeleton />;
  if (isError) {
    return (
      <span
        role="alert"
        className="text-[13px] text-[var(--text-muted)]"
        data-testid="topic-breadcrumb-error"
      >
        Couldn&apos;t load breadcrumb.
      </span>
    );
  }
  if (!ancestors || ancestors.length === 0) return null;

  const current = ancestors[ancestors.length - 1];
  const middleAncestors = ancestors.slice(0, -1); // everything except current
  const currentTitle = current?.title?.trim() || 'Untitled';

  // Decide truncation: when chain > threshold, split into [first] + [hidden]
  // + [last 2 ancestors], rendered with a Popover for the hidden middle.
  const shouldTruncate = ancestors.length > STATIC_TRUNCATION_THRESHOLD;
  const truncationFirst = shouldTruncate ? middleAncestors.slice(0, 1) : [];
  const truncationHidden = shouldTruncate
    ? middleAncestors.slice(1, middleAncestors.length - 2)
    : [];
  const truncationTail = shouldTruncate
    ? middleAncestors.slice(middleAncestors.length - 2)
    : middleAncestors;

  return (
    <nav
      aria-label="Breadcrumb"
      className="min-h-8 flex items-center gap-2 text-[13px]"
      data-testid="topic-breadcrumb"
    >
      <ol className="flex items-center gap-2 min-w-0">
        <li>
          <Link
            href={`/${workspaceSlug}`}
            aria-label="Workspace home"
            className="text-[13px] font-medium text-[var(--text-heading)] motion-safe:transition-colors hover:text-[var(--brand-primary)]"
          >
            Home
          </Link>
        </li>

        {shouldTruncate && truncationFirst[0] && (
          <Fragment key={`first-${truncationFirst[0].id}`}>
            <ChevronSeparator />
            <li>
              <SegmentLink
                workspaceSlug={workspaceSlug}
                ancestor={truncationFirst[0]}
                onAltClick={handleAltClick}
              />
            </li>
          </Fragment>
        )}

        {shouldTruncate && truncationHidden.length > 0 && (
          <Fragment key="truncation-popover">
            <ChevronSeparator />
            <li>
              <Popover>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    aria-label={`Show ${truncationHidden.length} hidden topics`}
                    data-testid="topic-breadcrumb-overflow"
                    className="inline-flex h-6 items-center rounded px-1.5 text-[var(--text-muted)] hover:bg-[var(--surface-input)] hover:text-[var(--text-heading)]"
                  >
                    …
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  align="start"
                  className="w-60 p-2"
                  data-testid="topic-breadcrumb-overflow-content"
                >
                  <ul className="flex flex-col gap-1">
                    {truncationHidden.map((a) => (
                      <li key={a.id}>
                        <Link
                          href={`/${workspaceSlug}/topics/${a.id}`}
                          onClick={(e) => {
                            if (e.altKey) {
                              e.preventDefault();
                              handleAltClick(a.id);
                            }
                          }}
                          className="block h-8 truncate rounded px-2 leading-8 text-[13px] text-[var(--text-heading)] hover:bg-[var(--surface-input)]"
                        >
                          {a.title?.trim() || 'Untitled'}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </PopoverContent>
              </Popover>
            </li>
          </Fragment>
        )}

        {truncationTail.map((ancestor) => (
          <Fragment key={ancestor.id}>
            <ChevronSeparator />
            <li className="min-w-0">
              <SegmentLink
                workspaceSlug={workspaceSlug}
                ancestor={ancestor}
                onAltClick={handleAltClick}
              />
            </li>
          </Fragment>
        ))}

        <ChevronSeparator />
        <li className="min-w-0">
          <span
            aria-current="page"
            aria-label={`${currentTitle}, current topic`}
            className="truncate text-[13px] font-semibold text-[#29a386] max-w-[240px] inline-block align-middle"
            data-testid="topic-breadcrumb-current"
          >
            {currentTitle}
          </span>
        </li>
      </ol>
    </nav>
  );
}
