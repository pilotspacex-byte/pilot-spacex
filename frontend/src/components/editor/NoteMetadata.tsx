'use client';

/**
 * NoteMetadata - Compact metadata bar showing project reference and linked issues.
 * Renders between InlineNoteHeader and the scrollable editor area.
 *
 * - Project: fetched via TanStack Query with progress indicator
 * - Linked issues: clickable badges with state color dots (max 5 visible)
 */
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { FolderKanban, Link2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { projectsApi } from '@/services/api/projects';
import type { LinkedIssueBrief } from '@/types';

/** Maximum number of linked issue badges shown before "+N more" */
const MAX_VISIBLE_ISSUES = 5;

export interface NoteMetadataProps {
  /** Optional project ID to fetch and display */
  projectId?: string;
  /** Issues linked to this note */
  linkedIssues: LinkedIssueBrief[];
  /** Workspace slug for building internal links */
  workspaceSlug: string;
  /** Additional CSS classes */
  className?: string;
}

export function NoteMetadata({
  projectId,
  linkedIssues,
  workspaceSlug,
  className,
}: NoteMetadataProps) {
  const { data: project } = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });

  // Nothing to show
  if (!projectId && linkedIssues.length === 0) return null;

  const total = project ? Math.max(project.issueCount, 1) : 1;
  const completedCount = project ? project.issueCount - project.openIssueCount : 0;
  const progress = project ? (completedCount / total) * 100 : 0;

  return (
    <div
      data-testid="note-metadata"
      className={cn(
        'flex flex-wrap items-center gap-2 px-4 py-1.5 text-xs text-muted-foreground',
        'border-b border-border/30 bg-background-subtle/50',
        className
      )}
    >
      {/* Project reference with progress bar */}
      {project && (
        <Link
          href={`/${workspaceSlug}/projects/${project.id}`}
          className="flex items-center gap-1.5 hover:text-foreground transition-colors"
          data-testid="note-metadata-project"
        >
          <FolderKanban className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          <span className="font-medium truncate max-w-[140px]">{project.name}</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1">
                <div
                  className="h-1.5 w-16 rounded-full bg-border overflow-hidden"
                  role="progressbar"
                  aria-valuenow={completedCount}
                  aria-valuemin={0}
                  aria-valuemax={project.issueCount}
                  aria-label={`${completedCount} of ${project.issueCount} issues completed`}
                >
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-[10px]">
                  {completedCount}/{project.issueCount}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent>
              {completedCount} of {project.issueCount} issues completed
            </TooltipContent>
          </Tooltip>
        </Link>
      )}

      {/* Separator */}
      {project && linkedIssues.length > 0 && (
        <span className="text-border" aria-hidden="true">
          ·
        </span>
      )}

      {/* Linked issues */}
      {linkedIssues.length > 0 && (
        <div className="flex items-center gap-1.5" data-testid="note-metadata-issues">
          <Link2 className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          <div className="flex flex-wrap items-center gap-1">
            {linkedIssues.slice(0, MAX_VISIBLE_ISSUES).map((issue) => (
              <Tooltip key={issue.id}>
                <TooltipTrigger asChild>
                  <Link
                    href={`/${workspaceSlug}/issues/${issue.id}`}
                    className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium hover:bg-accent/50 transition-colors"
                    data-testid={`note-metadata-issue-${issue.identifier}`}
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: issue.state.color }}
                      aria-hidden="true"
                    />
                    {issue.identifier}
                  </Link>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="max-w-[200px]">
                    <div className="font-medium">
                      {issue.identifier}: {issue.name}
                    </div>
                    <div className="text-muted-foreground">{issue.state.name}</div>
                  </div>
                </TooltipContent>
              </Tooltip>
            ))}
            {linkedIssues.length > MAX_VISIBLE_ISSUES && (
              <span className="text-[10px] text-muted-foreground" data-testid="note-metadata-more">
                +{linkedIssues.length - MAX_VISIBLE_ISSUES} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
