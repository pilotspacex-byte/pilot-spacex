/**
 * Extracted Issue Card Component.
 *
 * Displays an extracted issue with:
 * - Title and description
 * - Confidence tag badge (DD-048)
 * - Selection checkbox
 * - Optional labels and priority
 *
 * @module features/notes/components/ExtractedIssueCard
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T155
 */

import { observer } from 'mobx-react-lite';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { ConfidenceTagBadge } from '@/components/ui/confidence-tag-badge';
import { cn } from '@/lib/utils';
import type { ExtractedIssue } from '@/stores/ai';

interface ExtractedIssueCardProps {
  issue: ExtractedIssue;
  selected: boolean;
  onToggle: () => void;
}

const priorityLabels = {
  0: 'Urgent',
  1: 'High',
  2: 'Medium',
  3: 'Low',
  4: 'No Priority',
};

export const ExtractedIssueCard = observer(function ExtractedIssueCard({
  issue,
  selected,
  onToggle,
}: ExtractedIssueCardProps) {
  return (
    <Card
      className={cn(
        'cursor-pointer transition-all duration-200 hover:shadow-md',
        selected && 'border-primary bg-primary/5 shadow-sm'
      )}
      onClick={onToggle}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Checkbox checked={selected} className="mt-1" onClick={(e) => e.stopPropagation()} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <h4 className="font-medium text-sm">{issue.title}</h4>
              <ConfidenceTagBadge tag={issue.confidence_tag} score={issue.confidence_score} />
            </div>

            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">{issue.description}</p>

            <div className="flex flex-wrap gap-2 items-center">
              {issue.labels && issue.labels.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {issue.labels.map((label, i) => (
                    <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded-md font-medium">
                      {label}
                    </span>
                  ))}
                </div>
              )}

              {issue.priority !== undefined && (
                <span className="text-xs text-muted-foreground px-2 py-0.5 rounded-md bg-muted/50">
                  {priorityLabels[issue.priority as keyof typeof priorityLabels] || 'Medium'}
                </span>
              )}
            </div>

            {issue.rationale && (
              <p className="text-xs text-muted-foreground mt-2 italic">{issue.rationale}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
});
