/**
 * IssueUpdatePreview - Renders update_issue payload with markdown support.
 * Used by InlineApprovalCard for non-destructive issue update approvals.
 */
import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { MarkdownContent } from '../MessageList/MarkdownContent';

// Fields with markdown content — rendered with MarkdownContent
const MARKDOWN_FIELDS = new Set(['description', 'body', 'notes']);
// Internal identifiers hidden from the preview
const SKIP_FIELDS = new Set(['issue_id', 'workspace_id', 'operation']);

function formatLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

interface IssueUpdatePreviewProps {
  payload: Record<string, unknown>;
  className?: string;
}

export const IssueUpdatePreview = memo<IssueUpdatePreviewProps>(({ payload, className }) => {
  const fields = Object.entries(payload).filter(([key]) => !SKIP_FIELDS.has(key));

  if (fields.length === 0) return null;

  return (
    <div className={cn('space-y-3', className)}>
      {fields.map(([key, value]) => {
        const label = formatLabel(key);

        if (MARKDOWN_FIELDS.has(key) && typeof value === 'string') {
          return (
            <div key={key} className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {label}
              </span>
              <div className="rounded-md border bg-muted/20 px-3 py-2">
                <MarkdownContent content={value} />
              </div>
            </div>
          );
        }

        if (Array.isArray(value)) {
          return (
            <div key={key} className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">{label}:</span>
              <div className="flex flex-wrap gap-1">
                {value.map((item, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {String(item)}
                  </Badge>
                ))}
              </div>
            </div>
          );
        }

        return (
          <div key={key} className="flex items-start gap-2">
            <span className="text-xs font-medium text-muted-foreground shrink-0">{label}:</span>
            <span className="text-xs text-foreground">{String(value ?? '')}</span>
          </div>
        );
      })}
    </div>
  );
});

IssueUpdatePreview.displayName = 'IssueUpdatePreview';
