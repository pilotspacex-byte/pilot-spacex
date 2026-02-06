'use client';

/**
 * InlineNoteHeader - Sticky metadata bar (Notion-inspired)
 * Single line: [Notes > Title] · [Save Icon] · Date · Words · [Actions]
 *
 * Title is now handled separately as a content block (NoteTitleBlock)
 *
 * @see DD-013 Note-First Collaborative Workspace
 */
import { useCallback, useState } from 'react';
import { format } from 'date-fns';
import {
  ChevronRight,
  FileText,
  Share2,
  History,
  MoreHorizontal,
  Pin,
  PinOff,
  Copy,
  Download,
  Trash2,
  Sparkles,
  Cloud,
  CloudOff,
  Loader2,
} from 'lucide-react';
import Link from 'next/link';
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
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { User } from '@/types';

/**
 * Deterministic color mapping for topic tags.
 * Known tags map to specific color buckets; unknown tags use a hash-based fallback.
 */
const TAG_COLOR_MAP: Record<string, { bg: string; text: string }> = {
  // Category keywords -> primary (teal)
  'ai features': { bg: 'bg-primary', text: 'text-primary-foreground' },
  ai: { bg: 'bg-primary', text: 'text-primary-foreground' },
  features: { bg: 'bg-primary', text: 'text-primary-foreground' },

  // Topic keywords -> ai (blue)
  product: { bg: 'bg-ai', text: 'text-ai-foreground' },
  design: { bg: 'bg-ai', text: 'text-ai-foreground' },
  ux: { bg: 'bg-ai', text: 'text-ai-foreground' },

  // Domain keywords -> dark neutral
  architecture: { bg: 'bg-foreground', text: 'text-background' },
  engineering: { bg: 'bg-foreground', text: 'text-background' },
  infrastructure: { bg: 'bg-foreground', text: 'text-background' },
};

const DEFAULT_TAG_COLOR: { bg: string; text: string } = {
  bg: 'bg-primary',
  text: 'text-primary-foreground',
};

const FALLBACK_COLORS: { bg: string; text: string }[] = [
  DEFAULT_TAG_COLOR,
  { bg: 'bg-ai', text: 'text-ai-foreground' },
  { bg: 'bg-foreground', text: 'text-background' },
];

export function getTagColor(tag: string): { bg: string; text: string } {
  const key = tag.toLowerCase().trim();
  const mapped = TAG_COLOR_MAP[key];
  if (mapped) return mapped;
  // Simple hash for deterministic fallback
  const hash = key.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length] ?? DEFAULT_TAG_COLOR;
}

/** Save status type */
export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface InlineNoteHeaderProps {
  /** Note title (for breadcrumb display) */
  title: string;
  /** Note author */
  author?: User;
  /** Created timestamp */
  createdAt: string;
  /** Updated timestamp */
  updatedAt?: string;
  /** Word count */
  wordCount: number;
  /** Whether note is pinned */
  isPinned?: boolean;
  /** Whether note has AI-assisted edits */
  isAIAssisted?: boolean;
  /** Topic tags for the note */
  topics?: string[];
  /** Workspace slug for breadcrumb */
  workspaceSlug: string;
  /** Save status for cloud icon */
  saveStatus?: SaveStatus;
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
  /** Additional className for styling */
  className?: string;
}

/**
 * Save status icon component
 */
function SaveStatusIcon({ status }: { status: SaveStatus }) {
  switch (status) {
    case 'saving':
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            </span>
          </TooltipTrigger>
          <TooltipContent>Saving...</TooltipContent>
        </Tooltip>
      );
    case 'saved':
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center text-primary">
              <Cloud className="h-3.5 w-3.5" />
            </span>
          </TooltipTrigger>
          <TooltipContent>All changes saved</TooltipContent>
        </Tooltip>
      );
    case 'error':
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center text-destructive">
              <CloudOff className="h-3.5 w-3.5" />
            </span>
          </TooltipTrigger>
          <TooltipContent>Failed to save</TooltipContent>
        </Tooltip>
      );
    default:
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center text-muted-foreground/50">
              <Cloud className="h-3.5 w-3.5" />
            </span>
          </TooltipTrigger>
          <TooltipContent>Synced</TooltipContent>
        </Tooltip>
      );
  }
}

/**
 * InlineNoteHeader - Sticky metadata bar only
 * Title is now handled as a content block in the editor
 */
export function InlineNoteHeader({
  title,
  author: _author,
  createdAt,
  updatedAt: _updatedAt,
  wordCount,
  isPinned = false,
  isAIAssisted = false,
  topics,
  workspaceSlug,
  saveStatus = 'idle',
  onShare,
  onExport,
  onDelete,
  onTogglePin,
  onVersionHistory,
  disabled = false,
  className,
}: InlineNoteHeaderProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const createdAtDate = new Date(createdAt);

  const handleCopyLink = useCallback(() => {
    navigator.clipboard.writeText(window.location.href);
  }, []);

  return (
    <>
      {/* Fixed metadata bar - responsive padding matching editor content */}
      <div
        className={cn(
          'flex-shrink-0 bg-background/95 backdrop-blur-sm border-b border-border/50',
          // Responsive horizontal padding - matches editor content area
          'px-4',
          className
        )}
      >
        <div
          className={cn(
            'flex flex-wrap items-center text-muted-foreground',
            // Responsive gaps and text size
            'gap-1 sm:gap-1.5 md:gap-2 lg:gap-2.5',
            'text-[10px] sm:text-[11px] md:text-xs',
            // Responsive vertical padding
            'py-1 sm:py-1.5 md:py-2 lg:py-2.5'
          )}
        >
          {/* Breadcrumb */}
          <Link
            href={`/${workspaceSlug}/notes`}
            className="hover:text-foreground transition-colors flex items-center gap-0.5 sm:gap-1"
          >
            <FileText className="h-3 w-3 sm:h-3.5 sm:w-3.5 flex-shrink-0" />
            <span className="hidden sm:inline">Notes</span>
          </Link>
          <ChevronRight className="h-3 w-3 flex-shrink-0" />
          <span className="text-foreground truncate max-w-[80px] sm:max-w-[120px] md:max-w-[180px] lg:max-w-[240px] font-medium">
            {title || 'Untitled'}
          </span>

          {/* Separator */}
          <span className="text-border">·</span>

          {/* Save status icon */}
          <SaveStatusIcon status={saveStatus} />

          {/* Date - visible on sm+ */}
          <span className="hidden sm:inline text-border/60">·</span>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="hidden sm:flex items-center whitespace-nowrap">
                {format(createdAtDate, 'MMM d')}
              </span>
            </TooltipTrigger>
            <TooltipContent>Created: {format(createdAtDate, 'PPp')}</TooltipContent>
          </Tooltip>

          {/* Word count - visible on lg+ */}
          <span className="hidden lg:inline text-border/60">·</span>
          <span className="hidden lg:inline whitespace-nowrap">
            {wordCount.toLocaleString()} words
          </span>

          {/* Pin indicator - visible on sm+ */}
          {isPinned && (
            <>
              <span className="hidden sm:inline text-border/60">·</span>
              <Pin className="hidden sm:block h-3 w-3 text-amber-500 flex-shrink-0" />
            </>
          )}

          {/* AI badge - visible on md+ */}
          {isAIAssisted && (
            <>
              <span className="hidden md:inline text-border/60">·</span>
              <span className="hidden md:flex items-center gap-1 text-ai">
                <Sparkles className="h-3 w-3 flex-shrink-0" />
              </span>
            </>
          )}

          {/* Spacer */}
          <div className="flex-1 min-w-[8px]" />

          {/* Action buttons - responsive sizing */}
          <div className="flex items-center gap-0 sm:gap-0.5">
            {/* History - hidden on mobile */}
            {onVersionHistory && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onVersionHistory}
                    disabled={disabled}
                    className="hidden sm:flex h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                  >
                    <History className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>History</TooltipContent>
              </Tooltip>
            )}
            {/* Share - hidden on mobile */}
            {onShare && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onShare}
                    disabled={disabled}
                    className="hidden sm:flex h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                  >
                    <Share2 className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Share</TooltipContent>
              </Tooltip>
            )}
            {/* More menu - always visible */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  disabled={disabled}
                  className="h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                >
                  <MoreHorizontal className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                {/* Mobile-only: History and Share */}
                {onVersionHistory && (
                  <DropdownMenuItem onClick={onVersionHistory} className="sm:hidden">
                    <History className="mr-2 h-4 w-4" />
                    History
                  </DropdownMenuItem>
                )}
                {onShare && (
                  <DropdownMenuItem onClick={onShare} className="sm:hidden">
                    <Share2 className="mr-2 h-4 w-4" />
                    Share
                  </DropdownMenuItem>
                )}
                {(onVersionHistory || onShare) && <DropdownMenuSeparator className="sm:hidden" />}
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
                    className="text-destructive focus:text-destructive"
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

        {/* Topic tags */}
        {topics && topics.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 px-0 pb-2">
            {topics.map((tag) => {
              const color = getTagColor(tag);
              return (
                <Badge
                  key={tag}
                  className={cn(
                    'text-[10px] font-medium px-2 py-0.5 rounded-md border-0',
                    color.bg,
                    color.text
                  )}
                >
                  {tag}
                </Badge>
              );
            })}
          </div>
        )}
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
    </>
  );
}

export default InlineNoteHeader;
