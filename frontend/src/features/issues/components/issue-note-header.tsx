'use client';

/**
 * IssueNoteHeader - Minimal header for the note-first issue detail page.
 *
 * Matches the density of InlineNoteHeader from the note canvas.
 * Shows: ← | PS-42 [Type] [AI] | SaveStatus | CloneContext | ChatToggle | MoreMenu
 */
import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import {
  ArrowLeft,
  Loader2,
  MoreHorizontal,
  Network,
  Trash2,
  ExternalLink,
  Sparkles,
  MessageSquare,
  Link as LinkIcon,
  TerminalSquare,
} from 'lucide-react';
import { toast } from 'sonner';
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
import { copyToClipboard } from '@/lib/copy-context';
import { useIssueStore } from '@/stores';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { CloneContextPanel } from './clone-context-panel';
import type { ExportFormat } from './clone-context-panel';
import type { IssueType } from '@/types';

export interface IssueNoteHeaderProps {
  identifier: string;
  issueTitle?: string;
  issueType?: IssueType;
  aiGenerated?: boolean;
  isChatOpen: boolean;
  onBack: () => void;
  onToggleChat: () => void;
  onCopyLink: () => void;
  onDelete: () => void;
  onExport: (format: ExportFormat) => Promise<string | null>;
  onGeneratePlan?: () => Promise<void>;
  isGeneratingPlan?: boolean;
  stats?: {
    tasksCount: number;
    relatedIssuesCount: number;
    relatedDocsCount: number;
  };
}

const TYPE_LABELS: Record<string, string> = {
  bug: 'Bug',
  feature: 'Feature',
  improvement: 'Improvement',
  task: 'Task',
};

export const IssueNoteHeader = observer(function IssueNoteHeader({
  identifier,
  issueTitle,
  issueType,
  aiGenerated = false,
  isChatOpen,
  onBack,
  onToggleChat,
  onCopyLink,
  onDelete,
  onExport,
  onGeneratePlan,
  isGeneratingPlan = false,
  stats,
}: IssueNoteHeaderProps) {
  const issueStore = useIssueStore();

  const handleQuickCopy = useCallback(async () => {
    const content = await onExport('claude_code');
    if (!content) {
      toast.error('No context available yet', {
        description: 'Generate AI context first from the AI chat panel.',
      });
      return;
    }
    const ok = await copyToClipboard(content);
    if (ok) {
      toast.success('Context copied to clipboard', {
        description: 'Paste into Claude Code to start implementing.',
      });
    }
  }, [onExport]);

  return (
    <header className="flex items-center h-12 shrink-0 border-b border-border bg-background px-4">
      {/* Left cluster */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={onBack} aria-label="Back to issues">
          <ArrowLeft className="size-4" />
        </Button>
        <span className="min-w-0 truncate text-sm font-semibold font-mono text-foreground/70">
          {identifier}
        </span>
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

        <CloneContextPanel
          onExport={onExport}
          issueIdentifier={identifier}
          issueTitle={issueTitle}
          stats={stats}
        />

        {onGeneratePlan && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => void onGeneratePlan()}
                disabled={isGeneratingPlan}
                aria-label={
                  isGeneratingPlan ? 'Generating plan...' : 'Generate implementation plan'
                }
              >
                {isGeneratingPlan ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Network className="size-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Generate implementation plan</TooltipContent>
          </Tooltip>
        )}

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
            {/* Clone to Claude Code — quick copy, no panel */}
            <DropdownMenuItem onClick={() => void handleQuickCopy()} className="gap-2">
              <TerminalSquare className="size-4 shrink-0" />
              <div className="flex flex-col min-w-0">
                <span>Copy for Claude Code</span>
                <span className="text-[11px] text-muted-foreground font-normal">
                  Copies prompt format to clipboard
                </span>
              </div>
              <span className="ml-auto text-[11px] text-muted-foreground font-mono shrink-0">
                ⇧⌘C
              </span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem onClick={onCopyLink}>
              <LinkIcon className="mr-2 size-4" />
              Copy link
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => window.open(window.location.href, '_blank', 'noopener,noreferrer')}
            >
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
