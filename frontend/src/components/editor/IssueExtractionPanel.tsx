'use client';

/**
 * IssueExtractionPanel - Display AI-extracted issues from note content
 * Rainbow-bordered cards with confidence tags
 */
import { useCallback, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import {
  Sparkles,
  Check,
  Pencil,
  Link2,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Loader2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { IssuePriority } from '@/types';

export interface ExtractedIssue {
  id: string;
  title: string;
  description: string;
  suggestedLabels: string[];
  priority: IssuePriority;
  confidence: number;
  confidenceTag: 'recommended' | 'default' | 'current' | 'alternative';
  sourceBlockId: string;
  sourceText: string;
}

export interface IssueExtractionPanelProps {
  /** List of extracted issues */
  issues: ExtractedIssue[];
  /** Whether extraction is in progress */
  isExtracting?: boolean;
  /** Callback to create single issue */
  onCreateIssue: (issue: ExtractedIssue) => Promise<void>;
  /** Callback to create all issues */
  onCreateAll: () => Promise<void>;
  /** Callback when issue is dismissed */
  onDismiss?: (issueId: string) => void;
  /** Callback to scroll to source block */
  onScrollToSource?: (blockId: string) => void;
}

const CONFIDENCE_TAG_CONFIG = {
  recommended: {
    label: 'Recommended',
    color: 'text-green-600',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    gradient: 'from-green-500 via-emerald-500 to-teal-500',
  },
  default: {
    label: 'Default',
    color: 'text-blue-600',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    gradient: 'from-blue-500 via-indigo-500 to-purple-500',
  },
  current: {
    label: 'Current',
    color: 'text-amber-600',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    gradient: 'from-amber-500 via-orange-500 to-yellow-500',
  },
  alternative: {
    label: 'Alternative',
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
    gradient: 'from-gray-400 via-gray-500 to-gray-600',
  },
} as const;

const PRIORITY_CONFIG = {
  urgent: { label: 'Urgent', color: 'text-red-500', bgColor: 'bg-red-500/10' },
  high: { label: 'High', color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
  medium: { label: 'Medium', color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  low: { label: 'Low', color: 'text-blue-500', bgColor: 'bg-blue-500/10' },
  none: { label: 'None', color: 'text-gray-400', bgColor: 'bg-gray-400/10' },
} as const;

/**
 * Rainbow border wrapper for issue cards
 */
function RainbowBorder({
  gradient,
  children,
  className,
}: {
  gradient: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('relative rounded-lg p-[2px]', className)}>
      <div className={cn('absolute inset-0 rounded-lg bg-gradient-to-r opacity-60', gradient)} />
      <div className="relative rounded-lg bg-card">{children}</div>
    </div>
  );
}

/**
 * Single extracted issue card
 */
function IssueCard({
  issue,
  isCreating,
  onCreate,
  onDismiss,
  onScrollToSource,
}: {
  issue: ExtractedIssue;
  isCreating: boolean;
  onCreate: () => void;
  onDismiss?: () => void;
  onScrollToSource?: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [editedTitle, setEditedTitle] = useState(issue.title);

  const tagConfig = CONFIDENCE_TAG_CONFIG[issue.confidenceTag];
  const priorityConfig = PRIORITY_CONFIG[issue.priority];

  const handleCreate = useCallback(() => {
    setIsEditing(false);
    onCreate();
  }, [onCreate]);

  return (
    <RainbowBorder gradient={tagConfig.gradient}>
      <Card className="border-0 shadow-none">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 space-y-1">
              {/* Confidence tag */}
              <Badge
                variant="outline"
                className={cn('text-[10px]', tagConfig.bgColor, tagConfig.color)}
              >
                <Sparkles className="mr-1 h-3 w-3" />
                {tagConfig.label}
              </Badge>

              {/* Title */}
              {isEditing ? (
                <Input
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  className="text-base font-semibold"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setIsEditing(false);
                    }
                    if (e.key === 'Escape') {
                      setEditedTitle(issue.title);
                      setIsEditing(false);
                    }
                  }}
                />
              ) : (
                <CardTitle
                  className="text-base font-semibold leading-tight cursor-pointer hover:text-primary"
                  onClick={() => setIsEditing(true)}
                >
                  {editedTitle}
                </CardTitle>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="h-7 w-7"
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Edit before creating</TooltipContent>
              </Tooltip>

              {onDismiss && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={onDismiss}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Dismiss</TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          {/* Description preview */}
          <div>
            <p className={cn('text-sm text-muted-foreground', !isExpanded && 'line-clamp-2')}>
              {issue.description}
            </p>
            {issue.description.length > 120 && (
              <button
                className="text-xs text-primary hover:underline mt-1 flex items-center gap-0.5"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="h-3 w-3" /> Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3" /> Show more
                  </>
                )}
              </button>
            )}
          </div>

          {/* Labels and priority */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className={cn('text-[10px]', priorityConfig.bgColor, priorityConfig.color)}
            >
              {priorityConfig.label}
            </Badge>
            {issue.suggestedLabels.map((label) => (
              <Badge key={label} variant="secondary" className="text-[10px]">
                {label}
              </Badge>
            ))}
          </div>

          {/* Source link */}
          {onScrollToSource && (
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary"
              onClick={onScrollToSource}
            >
              <Link2 className="h-3 w-3" />
              View source in note
            </button>
          )}

          {/* Create button */}
          <Button size="sm" className="w-full" onClick={handleCreate} disabled={isCreating}>
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                Create Issue
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </RainbowBorder>
  );
}

/**
 * Empty state when no issues extracted
 */
function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
        <AlertCircle className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="font-medium text-foreground mb-1">No issues extracted</h3>
      <p className="text-sm text-muted-foreground max-w-[200px]">
        Select text and click &quot;Extract Issue&quot; to create issues from your notes.
      </p>
    </div>
  );
}

/**
 * IssueExtractionPanel component
 */
export const IssueExtractionPanel = observer(function IssueExtractionPanel({
  issues,
  isExtracting = false,
  onCreateIssue,
  onCreateAll,
  onDismiss,
  onScrollToSource,
}: IssueExtractionPanelProps) {
  const [creatingIds, setCreatingIds] = useState<Set<string>>(new Set());
  const [isCreatingAll, setIsCreatingAll] = useState(false);

  const handleCreateIssue = useCallback(
    async (issue: ExtractedIssue) => {
      setCreatingIds((prev) => new Set(prev).add(issue.id));
      try {
        await onCreateIssue(issue);
      } finally {
        setCreatingIds((prev) => {
          const next = new Set(prev);
          next.delete(issue.id);
          return next;
        });
      }
    },
    [onCreateIssue]
  );

  const handleCreateAll = useCallback(async () => {
    setIsCreatingAll(true);
    try {
      await onCreateAll();
    } finally {
      setIsCreatingAll(false);
    }
  }, [onCreateAll]);

  if (issues.length === 0 && !isExtracting) {
    return <EmptyState />;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-ai" />
          <span className="text-sm font-medium">Extracted Issues</span>
          <Badge variant="secondary" className="text-[10px]">
            {issues.length}
          </Badge>
        </div>
        {issues.length > 1 && (
          <Button size="sm" variant="outline" onClick={handleCreateAll} disabled={isCreatingAll}>
            {isCreatingAll ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                Create All
              </>
            )}
          </Button>
        )}
      </div>

      {/* Loading state */}
      {isExtracting && (
        <div className="flex items-center justify-center gap-2 border-b border-border py-3">
          <Loader2 className="h-4 w-4 animate-spin text-ai" />
          <span className="text-sm text-muted-foreground">Analyzing note content...</span>
        </div>
      )}

      {/* Issues list */}
      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4">
          <AnimatePresence mode="popLayout">
            {issues.map((issue) => (
              <motion.div
                key={issue.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
              >
                <IssueCard
                  issue={issue}
                  isCreating={creatingIds.has(issue.id)}
                  onCreate={() => handleCreateIssue(issue)}
                  onDismiss={onDismiss ? () => onDismiss(issue.id) : undefined}
                  onScrollToSource={
                    onScrollToSource ? () => onScrollToSource(issue.sourceBlockId) : undefined
                  }
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>
    </div>
  );
});

export default IssueExtractionPanel;
