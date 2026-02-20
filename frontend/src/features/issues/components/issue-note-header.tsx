'use client';

/**
 * IssueNoteHeader - Minimal header for the note-first issue detail page.
 *
 * Matches the density of InlineNoteHeader from the note canvas.
 * Shows: ← | PS-42 [Type] [AI] | SaveStatus | ChatToggle | MoreMenu
 */
import { observer } from 'mobx-react-lite';
import {
  ArrowLeft,
  MoreHorizontal,
  Trash2,
  ExternalLink,
  Sparkles,
  MessageSquare,
  Link as LinkIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SaveStatus } from '@/components/ui/save-status';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useIssueStore } from '@/stores';
import type { IssueType } from '@/types';

export interface IssueNoteHeaderProps {
  identifier: string;
  issueType?: IssueType;
  aiGenerated?: boolean;
  isChatOpen: boolean;
  onBack: () => void;
  onToggleChat: () => void;
  onCopyLink: () => void;
  onDelete: () => void;
}

const TYPE_LABELS: Record<string, string> = {
  bug: 'Bug',
  feature: 'Feature',
  improvement: 'Improvement',
  task: 'Task',
};

export const IssueNoteHeader = observer(function IssueNoteHeader({
  identifier,
  issueType,
  aiGenerated = false,
  isChatOpen,
  onBack,
  onToggleChat,
  onCopyLink,
  onDelete,
}: IssueNoteHeaderProps) {
  const issueStore = useIssueStore();

  return (
    <header className="flex items-center h-12 shrink-0 border-b border-border bg-background px-4">
      {/* Left cluster */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={onBack} aria-label="Back to issues">
          <ArrowLeft className="size-4" />
        </Button>
        <span className="text-sm font-medium font-mono text-muted-foreground">{identifier}</span>
        {issueType && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
            {TYPE_LABELS[issueType] ?? issueType}
          </Badge>
        )}
        {aiGenerated && (
          <Badge variant="outline" className="gap-1 text-ai border-ai/30 text-[10px] px-1.5 py-0">
            <Sparkles className="size-2.5" />
            AI
          </Badge>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right cluster */}
      <div className="flex items-center gap-1.5">
        <SaveStatus status={issueStore.aggregateSaveStatus} />

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleChat}
          className={cn(isChatOpen && 'bg-ai-muted text-ai')}
          aria-label={isChatOpen ? 'Close AI chat' : 'Open AI chat'}
          aria-pressed={isChatOpen}
        >
          <MessageSquare className="size-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="More actions">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onCopyLink}>
              <LinkIcon className="mr-2 size-4" />
              Copy link
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.open(window.location.href, '_blank')}>
              <ExternalLink className="mr-2 size-4" />
              Open in new tab
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 size-4" />
              Delete issue
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
});
