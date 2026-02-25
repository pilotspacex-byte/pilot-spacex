'use client';

import type React from 'react';
import { Sparkles, Brain, ShieldCheck, ListTodo } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { cn } from '@/lib/utils';
import type { Issue } from '@/types';
import type { AIContextResult } from '@/stores/ai/AIContextStore';
import { NotePreviewCard } from './note-preview-card';
import { IssueReferenceCard } from './issue-reference-card';

interface IssueChatEmptyStateProps {
  issue: Issue;
  aiContextResult: AIContextResult | null;
  workspaceSlug: string;
  onSendPrompt: (prompt: string) => void;
}

interface CommandCard {
  icon: React.ReactNode;
  label: string;
  description: string;
  prompt: string;
  alwaysShow: boolean;
  showWhenNoDescription?: boolean;
}

export const IssueChatEmptyState = observer(function IssueChatEmptyState({
  issue,
  aiContextResult,
  workspaceSlug,
  onSendPrompt,
}: IssueChatEmptyStateProps) {
  const noteLinks = issue.noteLinks ?? [];

  const commands: CommandCard[] = [
    {
      icon: <Sparkles className="size-4 text-ai" aria-hidden="true" />,
      label: 'Generate description',
      description: 'Create a structured description with acceptance criteria',
      prompt: `Generate a detailed description for issue "${issue.name}". Structure it with: Problem statement, Acceptance criteria, and Technical approach.`,
      alwaysShow: false,
      showWhenNoDescription: true,
    },
    {
      icon: <Brain className="size-4 text-muted-foreground" aria-hidden="true" />,
      label: 'Gather AI context',
      description: 'Analyze related issues, code deps, and implementation approach',
      prompt:
        'Analyze this issue and gather full implementation context. Include related issues, code dependencies, and suggested implementation approach.',
      alwaysShow: true,
    },
    {
      icon: <ShieldCheck className="size-4 text-muted-foreground" aria-hidden="true" />,
      label: 'QA this issue',
      description: 'Review completeness: title, description, acceptance criteria, fields',
      prompt:
        'Review this issue for completeness. Check: Is the title clear? Is there a description? Are acceptance criteria defined? Are there missing fields (assignee, priority, estimate)?',
      alwaysShow: true,
    },
    {
      icon: <ListTodo className="size-4 text-muted-foreground" aria-hidden="true" />,
      label: 'Decompose into tasks',
      description: 'Break down into atomic implementation tasks with estimates',
      prompt: 'Decompose this issue into atomic implementation tasks with estimates.',
      alwaysShow: true,
    },
  ];

  const visibleCommands = commands.filter((cmd) => {
    if (cmd.alwaysShow) return true;
    if (cmd.showWhenNoDescription && !issue.description) return true;
    return false;
  });

  const hasNoteLinks = noteLinks.length > 0;
  const hasRelatedIssues = aiContextResult !== null && aiContextResult.relatedIssues.length > 0;
  const showHint = !hasNoteLinks && aiContextResult === null;

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col items-center text-center gap-2 pt-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/80 to-ai/80 flex items-center justify-center">
          <Sparkles className="h-6 w-6 text-white" aria-hidden="true" />
        </div>
        <h3 className="text-base font-semibold">How can I help with this issue?</h3>
      </div>

      {/* Command grid */}
      <div className="grid grid-cols-2 gap-2">
        {visibleCommands.map((cmd) => (
          <button
            key={cmd.label}
            type="button"
            onClick={() => onSendPrompt(cmd.prompt)}
            className={cn(
              'border border-border rounded-xl p-3 flex flex-col gap-1',
              'hover:bg-muted/50 cursor-pointer transition-colors text-left'
            )}
          >
            {cmd.icon}
            <span className="text-sm font-medium">{cmd.label}</span>
            <span className="text-xs text-muted-foreground line-clamp-1">{cmd.description}</span>
          </button>
        ))}
      </div>

      {/* Related Notes */}
      {hasNoteLinks && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Related Notes
          </span>
          <div className="flex flex-col gap-1.5">
            {noteLinks.map((link) => (
              <NotePreviewCard
                key={link.id}
                noteId={link.noteId}
                noteTitle={link.noteTitle}
                linkType={link.linkType}
                workspaceSlug={workspaceSlug}
              />
            ))}
          </div>
        </div>
      )}

      {/* Related Issues from AI context */}
      {hasRelatedIssues && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Related Issues
          </span>
          <div className="flex flex-col gap-1.5">
            {aiContextResult.relatedIssues.map((rel) => (
              <IssueReferenceCard
                key={rel.issueId}
                issueId={rel.issueId}
                identifier={rel.identifier}
                title={rel.title}
                stateGroup={rel.stateGroup}
                relationType={rel.relationType}
                workspaceSlug={workspaceSlug}
              />
            ))}
          </div>
        </div>
      )}

      {/* Hint when no context available */}
      {showHint && (
        <p className="text-xs text-muted-foreground/60 text-center">
          Run &lsquo;Gather AI context&rsquo; to discover related notes and issues
        </p>
      )}
    </div>
  );
});
