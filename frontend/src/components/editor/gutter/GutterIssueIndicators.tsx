'use client';

/**
 * GutterIssueIndicators - Issue dots in the right track of the left gutter.
 *
 * Shows colored dots aligned with editor blocks that have linked issues.
 * Dot color reflects issue state. HoverCard shows issue details.
 * Click navigates to issue detail page.
 *
 * @see tmp/note-editor-plan.md Section 3a
 * @see tmp/note-editor-ui-design.md Section 3
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Editor } from '@tiptap/react';

import { cn } from '@/lib/utils';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card';
import type { LinkedIssueBrief, StateGroup } from '@/types';

export interface GutterIssueIndicatorsProps {
  editor: Editor;
  linkedIssues: LinkedIssueBrief[];
  onIssueClick?: (issueId: string) => void;
}

/** Issue state colors per UI design spec Section 3 */
const STATE_GROUP_COLORS: Record<StateGroup, string> = {
  backlog: '#9C9590',
  unstarted: '#5B8FC9',
  started: '#D9853F',
  completed: '#29A386',
  cancelled: '#D9534F',
};

/** Always show 1 dot + count badge to prevent vertical overflow into adjacent blocks */
const MAX_VISIBLE_DOTS = 1;

/**
 * Build a map from blockId to array of linked issues.
 * Sources: linkedIssues with blockId + InlineIssue nodes in editor.
 */
export function buildBlockIssueMap(
  linkedIssues: LinkedIssueBrief[],
  editor: Editor
): Map<string, LinkedIssueBrief[]> {
  const map = new Map<string, LinkedIssueBrief[]>();

  // From linkedIssues with blockId
  for (const issue of linkedIssues) {
    if (issue.blockId) {
      const list = map.get(issue.blockId) ?? [];
      list.push(issue);
      map.set(issue.blockId, list);
    }
  }

  // From InlineIssue nodes in editor
  editor.state.doc.descendants((node) => {
    if (node.type.name === 'inlineIssue' && node.attrs.sourceBlockId) {
      const issueId = node.attrs.issueId as string;
      const blockId = node.attrs.sourceBlockId as string;
      const match = linkedIssues.find((i) => i.id === issueId);
      if (match) {
        const list = map.get(blockId) ?? [];
        if (!list.some((i) => i.id === issueId)) {
          list.push(match);
          map.set(blockId, list);
        }
      }
    }
    return true;
  });

  return map;
}

function getStateColor(stateGroup: StateGroup): string {
  return STATE_GROUP_COLORS[stateGroup] ?? STATE_GROUP_COLORS.backlog;
}

/** Single issue dot with HoverCard */
function IssueDot({
  issue,
  onIssueClick,
}: {
  issue: LinkedIssueBrief;
  onIssueClick?: (issueId: string) => void;
}) {
  const color = getStateColor(issue.state.group);

  return (
    <HoverCard openDelay={300} closeDelay={100}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          onClick={() => onIssueClick?.(issue.id)}
          className={cn(
            'flex items-center justify-center',
            'w-6 h-6 cursor-pointer',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 rounded-full',
            'transition-transform duration-150 ease-out hover:scale-125'
          )}
          aria-label={`${issue.identifier}: ${issue.name} (${issue.state.name})`}
        >
          <span
            className="rounded-full block w-2 h-2"
            style={{
              backgroundColor: color,
            }}
          />
        </button>
      </HoverCardTrigger>
      <HoverCardContent side="right" align="start" className="w-[280px] p-3">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold font-mono text-foreground">
              {issue.identifier}
            </span>
            <span
              className="text-[10px] font-medium px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: `${color}20`,
                color,
              }}
            >
              {issue.state.name}
            </span>
          </div>
          <p className="text-[13px] font-medium text-foreground line-clamp-2 leading-snug">
            {issue.name}
          </p>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="capitalize">{issue.priority}</span>
            {issue.assignee && (
              <>
                <span>·</span>
                <span>{issue.assignee.displayName ?? issue.assignee.email}</span>
              </>
            )}
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

/** Overflow badge showing "+N" for blocks with many issues */
function OverflowBadge({ count }: { count: number }) {
  return (
    <div className="flex items-center justify-center w-6 h-6">
      <span
        className={cn(
          'inline-flex items-center justify-center',
          'min-w-4 h-3 px-1 rounded-md',
          'bg-muted border border-border',
          'text-[9px] font-semibold text-muted-foreground'
        )}
      >
        {count}+
      </span>
    </div>
  );
}

export function GutterIssueIndicators({
  editor,
  linkedIssues,
  onIssueClick,
}: GutterIssueIndicatorsProps) {
  // Use state for positions (same pattern as GutterTOC)
  const [positions, setPositions] = useState<Map<string, number>>(new Map());
  const rafRef = useRef<number>(0);

  const blockIssueMap = useMemo(
    () => buildBlockIssueMap(linkedIssues, editor),
    [linkedIssues, editor]
  );

  // Compute block positions (debounced via rAF)
  useEffect(() => {
    if (!editor || blockIssueMap.size === 0) return;

    const recalc = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const cache = new Map<string, number>();
        for (const blockId of blockIssueMap.keys()) {
          const el = editor.view.dom.querySelector(
            `[data-block-id="${CSS.escape(blockId)}"]`
          ) as HTMLElement | null;
          if (el) {
            cache.set(blockId, el.offsetTop);
          }
        }
        setPositions(cache);
      });
    };

    recalc();
    editor.on('update', recalc);
    return () => {
      editor.off('update', recalc);
      cancelAnimationFrame(rafRef.current);
    };
  }, [editor, blockIssueMap]);

  if (blockIssueMap.size === 0) return null;

  const entries = Array.from(blockIssueMap.entries());

  return (
    <div className="relative w-7 flex-shrink-0">
      {entries.map(([blockId, issues]) => {
        const top = positions.get(blockId);
        if (top === undefined) return null;

        const firstIssue = issues[0]!;
        const extraCount = issues.length - MAX_VISIBLE_DOTS;

        return (
          <div key={blockId} className="absolute left-0 w-7 flex items-center" style={{ top }}>
            <IssueDot issue={firstIssue} onIssueClick={onIssueClick} />
            {extraCount > 0 && <OverflowBadge count={extraCount} />}
          </div>
        );
      })}
    </div>
  );
}
