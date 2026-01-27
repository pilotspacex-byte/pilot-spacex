/**
 * IssuePreview - Preview issue data for approval
 */

import { memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface IssuePreviewData {
  title?: unknown;
  description?: unknown;
  priority?: unknown;
  type?: unknown;
  labels?: unknown;
  estimatedHours?: unknown;
}

interface IssuePreviewProps {
  issue: IssuePreviewData | Record<string, unknown>;
  className?: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'destructive',
  high: 'orange',
  medium: 'yellow',
  low: 'blue',
  none: 'secondary',
};

const TYPE_COLORS: Record<string, string> = {
  bug: 'destructive',
  feature: 'default',
  improvement: 'secondary',
  task: 'outline',
};

export const IssuePreview = memo<IssuePreviewProps>(({ issue, className }) => {
  // Safely extract values with type guards
  const title = typeof issue.title === 'string' ? issue.title : 'Untitled Issue';
  const priority = typeof issue.priority === 'string' ? issue.priority : undefined;
  const type = typeof issue.type === 'string' ? issue.type : undefined;
  const description = typeof issue.description === 'string' ? issue.description : undefined;
  const estimatedHours =
    typeof issue.estimatedHours === 'number' ? issue.estimatedHours : undefined;
  const labels = Array.isArray(issue.labels)
    ? (issue.labels.filter((l): l is string => typeof l === 'string') as string[])
    : undefined;

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base leading-tight">{title}</CardTitle>

        <div className="flex flex-wrap items-center gap-2 pt-2">
          {priority && (
            <Badge
              variant={
                (PRIORITY_COLORS[priority] as
                  | 'default'
                  | 'destructive'
                  | 'outline'
                  | 'secondary') ?? 'secondary'
              }
            >
              {priority}
            </Badge>
          )}

          {type && (
            <Badge
              variant={
                (TYPE_COLORS[type] as 'default' | 'destructive' | 'outline' | 'secondary') ??
                'secondary'
              }
            >
              {type}
            </Badge>
          )}

          {estimatedHours !== undefined && <Badge variant="outline">{estimatedHours}h</Badge>}
        </div>
      </CardHeader>

      {(description || (labels && labels.length > 0)) && (
        <>
          <Separator />
          <CardContent className="pt-4 space-y-3">
            {description && (
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Description</span>
                <p className="text-sm text-foreground whitespace-pre-wrap">{description}</p>
              </div>
            )}

            {labels && labels.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Labels</span>
                <div className="flex flex-wrap gap-1">
                  {labels.map((label) => (
                    <Badge key={label} variant="secondary" className="text-xs">
                      {label}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </>
      )}
    </Card>
  );
});

IssuePreview.displayName = 'IssuePreview';
