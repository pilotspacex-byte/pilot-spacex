'use client';

/**
 * RichNoteHeader - Header component for note detail view
 * Editable title, metadata, stats, breadcrumb, and actions
 */
import { useCallback, useState, useRef, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { format } from 'date-fns';
import {
  ChevronRight,
  Clock,
  FileText,
  Share2,
  Download,
  Trash2,
  MoreHorizontal,
  Pin,
  PinOff,
  Copy,
  History,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { User } from '@/types';

export interface RichNoteHeaderProps {
  /** Note title */
  title: string;
  /** Note author */
  author?: User;
  /** Created timestamp */
  createdAt: string;
  /** Updated timestamp */
  updatedAt: string;
  /** Word count */
  wordCount: number;
  /** Whether note is pinned */
  isPinned: boolean;
  /** Whether note has AI-assisted edits */
  isAIAssisted?: boolean;
  /** Topic tag for the note */
  topicTag?: string;
  /** Workspace slug for breadcrumb */
  workspaceSlug: string;
  /** Workspace name for breadcrumb */
  workspaceName?: string;
  /** Project name (optional) */
  projectName?: string;
  /** Project slug (optional) */
  projectSlug?: string;
  /** Callback when title changes */
  onTitleChange: (title: string) => void;
  /** Callback for share action */
  onShare?: () => void;
  /** Callback for export action */
  onExport?: () => void;
  /** Callback for delete action */
  onDelete?: () => void;
  /** Callback for pin toggle */
  onTogglePin?: () => void;
  /** Callback for version history */
  onVersionHistory?: () => void;
  /** Whether actions are disabled */
  disabled?: boolean;
}

/**
 * Calculate reading time from word count
 */
function calculateReadingTime(wordCount: number): number {
  const wordsPerMinute = 200;
  return Math.ceil(wordCount / wordsPerMinute);
}

/**
 * Editable title component
 */
function EditableTitle({
  title,
  onChange,
  disabled,
}: {
  title: string;
  onChange: (title: string) => void;
  disabled?: boolean;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  // Start editing - set initial value from title
  const startEditing = useCallback(() => {
    setEditValue(title);
    setIsEditing(true);
  }, [title]);

  const handleSave = useCallback(() => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== title) {
      onChange(trimmed);
    } else {
      setEditValue(title);
    }
    setIsEditing(false);
  }, [editValue, title, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSave();
      }
      if (e.key === 'Escape') {
        setEditValue(title);
        setIsEditing(false);
      }
    },
    [handleSave, title]
  );

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        data-testid="note-title-input"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className={cn(
          'w-full bg-transparent font-display text-[2.25rem] font-semibold text-foreground',
          'border-b-2 border-primary outline-none',
          'py-1 leading-tight tracking-tight'
        )}
        style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.03em' }}
        disabled={disabled}
      />
    );
  }

  return (
    <h1
      className={cn(
        'font-display text-[2.25rem] font-semibold text-foreground leading-tight tracking-tight',
        !disabled && 'cursor-text hover:bg-accent/50 rounded px-1 -mx-1 transition-colors'
      )}
      style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.03em' }}
      onClick={() => !disabled && startEditing()}
    >
      {title || 'Untitled'}
    </h1>
  );
}

/**
 * RichNoteHeader component
 */
export const RichNoteHeader = observer(function RichNoteHeader({
  title,
  author,
  createdAt,
  updatedAt,
  wordCount,
  isPinned,
  isAIAssisted = false,
  topicTag,
  workspaceSlug,
  workspaceName = 'Workspace',
  projectName,
  projectSlug,
  onTitleChange,
  onShare,
  onExport,
  onDelete,
  onTogglePin,
  onVersionHistory,
  disabled = false,
}: RichNoteHeaderProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const readingTime = calculateReadingTime(wordCount);
  const createdAtDate = new Date(createdAt);
  const updatedAtDate = new Date(updatedAt);
  const wasModified = updatedAt !== createdAt;

  const handleCopyLink = useCallback(() => {
    navigator.clipboard.writeText(window.location.href);
  }, []);

  return (
    <div className="border-b border-border-subtle bg-background">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 px-6 py-2 text-sm text-muted-foreground">
        <Link href={`/${workspaceSlug}`} className="hover:text-foreground transition-colors">
          {workspaceName}
        </Link>
        <ChevronRight className="h-4 w-4" />
        {projectName && projectSlug ? (
          <>
            <Link
              href={`/${workspaceSlug}/projects/${projectSlug}`}
              className="hover:text-foreground transition-colors"
            >
              {projectName}
            </Link>
            <ChevronRight className="h-4 w-4" />
          </>
        ) : (
          <>
            <Link
              href={`/${workspaceSlug}/notes`}
              className="hover:text-foreground transition-colors"
            >
              Notes
            </Link>
            <ChevronRight className="h-4 w-4" />
          </>
        )}
        <span className="text-foreground truncate max-w-[200px]">{title || 'Untitled'}</span>
      </div>

      {/* Main header */}
      <div className="flex items-start justify-between gap-4 px-6 py-4">
        <div className="flex-1 min-w-0 space-y-2">
          {/* Title */}
          <div className="flex items-center gap-2">
            <EditableTitle title={title} onChange={onTitleChange} disabled={disabled} />
            {isPinned && (
              <Tooltip>
                <TooltipTrigger>
                  <Pin className="h-4 w-4 text-amber-500" />
                </TooltipTrigger>
                <TooltipContent>Pinned note</TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* Metadata row - Prototype v4 style with reading time pill */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[0.8rem] text-muted-foreground">
            {/* Date */}
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {format(createdAtDate, 'MMM d, yyyy')}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1">
                  <p>Created: {format(createdAtDate, 'PPp')}</p>
                  {wasModified && <p>Modified: {format(updatedAtDate, 'PPp')}</p>}
                </div>
              </TooltipContent>
            </Tooltip>

            {/* Author with Avatar */}
            {author && (
              <span className="flex items-center gap-1.5 text-foreground">
                <Avatar className="h-5 w-5">
                  <AvatarImage src={author.avatarUrl} alt={author.name || 'Author'} />
                  <AvatarFallback className="text-[0.6rem] bg-primary/10 text-primary">
                    {(author.name || 'U').slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {author.name}
              </span>
            )}

            {/* Word count */}
            <span className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              {wordCount.toLocaleString()} words
            </span>

            {/* Reading time pill - AI styled */}
            <span className="reading-time-pill">
              <Clock className="h-3 w-3" />
              {readingTime} min read
            </span>

            {/* Topic tag */}
            {topicTag && <span className="font-medium text-primary">{topicTag}</span>}

            {/* AI attribution badge - inline with metadata */}
            {isAIAssisted && (
              <span className="ai-attribution">
                <Sparkles className="h-3 w-3" />
                You + AI
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {onVersionHistory && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={onVersionHistory}
                  disabled={disabled}
                  data-testid="version-history-button"
                >
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Version History</TooltipContent>
            </Tooltip>
          )}
          {onShare && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" onClick={onShare} disabled={disabled}>
                  <Share2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Share</TooltipContent>
            </Tooltip>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" disabled={disabled}>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {onTogglePin && (
                <DropdownMenuItem onClick={onTogglePin}>
                  {isPinned ? (
                    <>
                      <PinOff className="mr-2 h-4 w-4" />
                      Unpin
                    </>
                  ) : (
                    <>
                      <Pin className="mr-2 h-4 w-4" />
                      Pin to top
                    </>
                  )}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={handleCopyLink}>
                <Copy className="mr-2 h-4 w-4" />
                Copy link
              </DropdownMenuItem>
              {onExport && (
                <DropdownMenuItem onClick={onExport}>
                  <Download className="mr-2 h-4 w-4" />
                  Export
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              {onDelete && (
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete note</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{title}&rdquo;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onDelete?.();
                setShowDeleteDialog(false);
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
});

export default RichNoteHeader;
