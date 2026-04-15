/**
 * IssuePreviewItem - Collapsible per-issue card in the BatchPreviewCard.
 *
 * CRITICAL: Must NOT be wrapped in observer() — plain React.memo + useState only.
 * Same constraint as IssueEditorContent per CLAUDE.md TipTap rule and RESEARCH Pitfall 1.
 *
 * Phase 75: Chat-to-issue pipeline (CIP-03, CIP-04)
 */

import { memo, useState, useCallback, useRef } from 'react';
import { X, ChevronDown, CheckSquare, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { ProposedIssue } from '@/stores/ai/types/events';

/** Priority badge colors per UI-SPEC.md Color section */
const PRIORITY_STYLES: Record<ProposedIssue['priority'], { label: string; className: string }> = {
  urgent: { label: 'Urgent', className: 'bg-[#fef2f2] text-[#d9534f] border-[#fca5a5]' },
  high: { label: 'High', className: 'bg-[#fff7ed] text-[#d9853f] border-[#fdba74]' },
  medium: { label: 'Medium', className: 'bg-[#fefce8] text-[#c4a035] border-[#fde047]' },
  low: { label: 'Low', className: 'bg-[#eff6ff] text-[#5b8fc9] border-[#93c5fd]' },
  none: { label: 'None', className: 'bg-[#f9fafb] text-[#9c9590] border-[#e5e7eb]' },
};

const PRIORITY_ORDER: ProposedIssue['priority'][] = ['none', 'low', 'medium', 'high', 'urgent'];

export interface IssuePreviewItemProps {
  issue: ProposedIssue;
  index: number;
  onRemove: (index: number) => void;
  onUpdate: (index: number, updates: Partial<ProposedIssue>) => void;
}

/**
 * Per-issue collapsible card in the BatchPreviewCard.
 * Uses React.memo + useState for local state. NOT observer().
 */
export const IssuePreviewItem = memo<IssuePreviewItemProps>(function IssuePreviewItem({
  issue,
  index,
  onRemove,
  onUpdate,
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const descRef = useRef<HTMLTextAreaElement>(null);

  const { priority } = issue;
  const priorityStyle = PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.none;

  const handleRemove = useCallback(() => {
    setIsRemoving(true);
    // 150ms fade-out before calling onRemove
    setTimeout(() => {
      onRemove(index);
    }, 150);
  }, [index, onRemove]);

  const handleTitleBlur = useCallback(() => {
    if (titleRef.current && titleRef.current.value !== issue.title) {
      onUpdate(index, { title: titleRef.current.value });
    }
  }, [index, issue.title, onUpdate]);

  const handleDescBlur = useCallback(() => {
    if (descRef.current && descRef.current.value !== issue.description) {
      onUpdate(index, { description: descRef.current.value });
    }
  }, [index, issue.description, onUpdate]);

  const handlePriorityChange = useCallback(
    (newPriority: ProposedIssue['priority']) => {
      onUpdate(index, { priority: newPriority });
    },
    [index, onUpdate]
  );

  return (
    <div
      role="listitem"
      className={cn(
        'transition-opacity duration-150',
        isRemoving && 'opacity-0'
      )}
    >
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        {/* Collapsed row — 44px touch target */}
        <div className="flex items-center gap-2 px-3 py-2.5 min-h-[44px]">
          {/* Priority badge */}
          <span
            className={cn(
              'shrink-0 px-1.5 py-0.5 rounded text-[11px] font-mono border leading-none',
              priorityStyle.className
            )}
          >
            {priorityStyle.label}
          </span>

          {/* Title (truncated in collapsed state) */}
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex-1 text-left text-[15px] font-semibold leading-snug truncate text-foreground hover:text-foreground/80 transition-colors min-w-0"
              aria-expanded={isExpanded}
              aria-controls={`issue-item-content-${index}`}
            >
              {issue.title || 'Untitled issue'}
            </button>
          </CollapsibleTrigger>

          {/* Remove button */}
          <button
            type="button"
            aria-label={`Remove "${issue.title || 'Untitled issue'}" from batch`}
            onClick={handleRemove}
            className="shrink-0 p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X size={14} />
          </button>

          {/* Expand chevron */}
          <CollapsibleTrigger asChild>
            <button
              type="button"
              aria-label={isExpanded ? 'Collapse issue' : 'Expand issue'}
              className="shrink-0 p-1 rounded text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ChevronDown
                size={14}
                className={cn('transition-transform duration-200', isExpanded && 'rotate-180')}
              />
            </button>
          </CollapsibleTrigger>
        </div>

        {/* Expanded content */}
        <CollapsibleContent id={`issue-item-content-${index}`}>
          <div className="px-3 pb-3 space-y-3">
            {/* Editable title */}
            <div>
              <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1 block">
                Title
              </label>
              <input
                ref={titleRef}
                type="text"
                defaultValue={issue.title}
                onBlur={handleTitleBlur}
                className="w-full text-[15px] font-semibold bg-transparent border-0 border-b border-transparent focus:border-b focus:border-ring focus:outline-none pb-0.5 transition-colors text-foreground placeholder:text-muted-foreground"
                placeholder="Issue title"
              />
            </div>

            {/* Editable description */}
            <div>
              <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1 block">
                Description
              </label>
              <textarea
                ref={descRef}
                defaultValue={issue.description}
                onBlur={handleDescBlur}
                rows={3}
                className="w-full text-sm bg-transparent border border-transparent focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring rounded px-1 py-0.5 resize-none transition-colors text-foreground placeholder:text-muted-foreground"
                placeholder="Describe the issue..."
              />
            </div>

            {/* Acceptance criteria */}
            {issue.acceptance_criteria && issue.acceptance_criteria.length > 0 && (
              <div>
                <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                  Acceptance Criteria
                </label>
                <ul className="space-y-1.5" role="list">
                  {issue.acceptance_criteria.map((ac, acIdx) => (
                    <li key={acIdx} className="flex items-start gap-2">
                      <span
                        role="checkbox"
                        aria-checked={ac.met}
                        aria-label={ac.criterion}
                        className="mt-0.5 shrink-0"
                      >
                        {ac.met ? (
                          <CheckSquare size={14} className="text-primary" />
                        ) : (
                          <Square size={14} className="text-muted-foreground" />
                        )}
                      </span>
                      <span className="text-sm text-foreground leading-snug">{ac.criterion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Priority selector */}
            <div>
              <label className="text-[11px] font-mono text-muted-foreground uppercase tracking-wide mb-1.5 block">
                Priority
              </label>
              <div className="flex flex-wrap gap-1.5">
                {PRIORITY_ORDER.map((p) => {
                  const style = PRIORITY_STYLES[p];
                  const isActive = priority === p;
                  return (
                    <button
                      key={p}
                      type="button"
                      onClick={() => handlePriorityChange(p)}
                      className={cn(
                        'px-2 py-0.5 rounded text-[11px] font-mono border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        style.className,
                        isActive ? 'ring-2 ring-offset-1 ring-current' : 'opacity-60 hover:opacity-100'
                      )}
                      aria-pressed={isActive}
                    >
                      {style.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
});

IssuePreviewItem.displayName = 'IssuePreviewItem';
