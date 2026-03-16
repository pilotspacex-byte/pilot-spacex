'use client';

/**
 * IssueGraph — inline relationship panel for the issue detail page.
 *
 * Renders three sections:
 *   Project     — pill linking to the project page
 *   Notes       — noteLinks grouped by extracted / referenced / related / inline
 *   Relations   — issue-to-issue links (blocks / blocked_by / duplicates / related)
 *
 * Presentational component: receives `relations` and `relationsLoading` as props
 * from the parent (IssueEditorContent) so the parent can include the relation
 * count in its CollapsibleSection header badge.
 */

import { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp, Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import { IssueReferenceCard } from './issue-reference-card';
import type { Issue, IssueRelation, NoteIssueLink } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const COLLAPSE_THRESHOLD = 3;

const NOTE_LINK_TYPE_LABEL: Record<NoteIssueLink['linkType'], string> = {
  extracted: 'Extracted from',
  referenced: 'Referenced in',
  related: 'Related to',
  inline: 'Inline in',
};

// Map IssueRelation.linkType → IssueReferenceCard relationType
function toCardRelationType(
  linkType: IssueRelation['linkType']
): 'blocks' | 'blocked_by' | 'duplicates' | 'relates' {
  if (linkType === 'blocks') return 'blocks';
  if (linkType === 'blocked_by') return 'blocked_by';
  if (linkType === 'duplicates') return 'duplicates';
  return 'relates';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function SectionHeader({ label, count }: { label: string; count: number }) {
  return (
    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
      {label}
      {count > 0 && (
        <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs tabular-nums">
          {count}
        </span>
      )}
    </p>
  );
}

interface ShowMoreButtonProps {
  expanded: boolean;
  hiddenCount: number;
  onToggle: () => void;
}

function ShowMoreButton({ expanded, hiddenCount, onToggle }: ShowMoreButtonProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {expanded ? (
        <>
          <ChevronUp className="size-3" />
          Show less
        </>
      ) : (
        <>
          <ChevronDown className="size-3" />
          Show {hiddenCount} more
        </>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface IssueGraphProps {
  issue: Issue;
  workspaceId: string;
  workspaceSlug: string;
  /** Relations fetched by the parent via useIssueRelations. */
  relations: IssueRelation[];
  /** True while the parent's useIssueRelations query is loading. */
  relationsLoading: boolean;
}

// ---------------------------------------------------------------------------
// IssueGraph (non-observer, presentational)
// ---------------------------------------------------------------------------
export function IssueGraph({ issue, workspaceSlug, relations, relationsLoading }: IssueGraphProps) {
  const [notesExpanded, setNotesExpanded] = useState(false);
  const [relationsExpanded, setRelationsExpanded] = useState(false);

  const noteLinks = issue.noteLinks ?? [];
  const displayedNotes = notesExpanded ? noteLinks : noteLinks.slice(0, COLLAPSE_THRESHOLD);
  const displayedRelations = relationsExpanded ? relations : relations.slice(0, COLLAPSE_THRESHOLD);

  return (
    <div className="space-y-5 pt-1">
      {/* ── Project ── */}
      <div>
        <SectionHeader label="Project" count={issue.project ? 1 : 0} />
        {issue.project ? (
          <Link
            href={`/${workspaceSlug}/projects/${issue.project.id}`}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full border border-border',
              'bg-muted/50 px-2.5 py-1 text-xs font-medium text-foreground',
              'hover:bg-muted transition-colors focus-visible:outline-none',
              'focus-visible:ring-2 focus-visible:ring-ring'
            )}
          >
            <Folder className="size-3 text-[#29A386]" aria-hidden="true" />
            {issue.project.name}
          </Link>
        ) : (
          <p className="text-xs text-muted-foreground">No project assigned</p>
        )}
      </div>

      {/* ── Notes ── */}
      <div>
        <SectionHeader label="Notes" count={noteLinks.length} />
        {noteLinks.length === 0 ? (
          <p className="text-xs text-muted-foreground">No linked notes</p>
        ) : (
          <>
            <ul className="space-y-1" aria-label="Linked notes">
              {displayedNotes.map((link) => (
                <li key={link.id}>
                  <Link
                    href={`/${workspaceSlug}/notes/${link.noteId}`}
                    className={cn(
                      'flex items-center gap-2 rounded-md border border-border px-2.5 py-1.5',
                      'text-sm hover:bg-muted/50 transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                    )}
                  >
                    <span
                      className={cn(
                        'shrink-0 rounded-full px-1.5 py-0.5 text-xs font-medium',
                        'bg-[#29A386]/10 text-[#29A386]'
                      )}
                    >
                      {NOTE_LINK_TYPE_LABEL[link.linkType]}
                    </span>
                    <span className="flex-1 truncate text-foreground">
                      {link.noteTitle || 'Untitled note'}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            {noteLinks.length > COLLAPSE_THRESHOLD && (
              <ShowMoreButton
                expanded={notesExpanded}
                hiddenCount={noteLinks.length - COLLAPSE_THRESHOLD}
                onToggle={() => setNotesExpanded((v) => !v)}
              />
            )}
          </>
        )}
      </div>

      {/* ── Related Issues ── */}
      <div>
        <SectionHeader label="Relations" count={relations.length} />
        {relationsLoading ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : relations.length === 0 ? (
          <p className="text-xs text-muted-foreground">No related issues</p>
        ) : (
          <>
            <ul className="space-y-1.5" aria-label="Related issues">
              {displayedRelations.map((relation) => (
                <li key={relation.id}>
                  <IssueReferenceCard
                    issueId={relation.relatedIssue.id}
                    identifier={relation.relatedIssue.identifier}
                    title={relation.relatedIssue.name}
                    stateGroup={relation.relatedIssue.state.group}
                    relationType={toCardRelationType(relation.linkType)}
                    workspaceSlug={workspaceSlug}
                  />
                </li>
              ))}
            </ul>
            {relations.length > COLLAPSE_THRESHOLD && (
              <ShowMoreButton
                expanded={relationsExpanded}
                hiddenCount={relations.length - COLLAPSE_THRESHOLD}
                onToggle={() => setRelationsExpanded((v) => !v)}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
