'use client';

/**
 * AIContext - Display AI-generated context for an issue.
 *
 * T211: Main container component for AI context tab in issue detail view.
 * Shows summary, related items, code references, tasks, Claude Code prompt,
 * and chat interface for refinement.
 *
 * @example
 * ```tsx
 * <Tabs>
 *   <TabsContent value="ai-context">
 *     <AIContext issueId={issue.id} />
 *   </TabsContent>
 * </Tabs>
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  RefreshCw,
  Download,
  Loader2,
  AlertCircle,
  Sparkles,
  FileText,
  Code,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { ContextItemList, type RelatedItem } from './ContextItemList';
import { TaskChecklist, type TaskItem } from './TaskChecklist';
import { ClaudeCodePrompt } from './ClaudeCodePrompt';
import { ContextChat } from './ContextChat';
import { useAIContext, useAIContextChat, useExportContext } from '@/features/issues/hooks';

// ============================================================================
// Types
// ============================================================================

export interface CodeReference {
  /** Unique identifier */
  id: string;
  /** File path */
  filePath: string;
  /** Start line */
  lineStart: number;
  /** End line */
  lineEnd: number;
  /** Code content */
  content: string;
  /** Relevance score (0-1) */
  relevance: number;
  /** Language for syntax highlighting */
  language?: string;
}

export interface AIContextData {
  /** Summary of the issue context */
  summary: string;
  /** Related issues */
  relatedIssues: RelatedItem[];
  /** Related notes */
  relatedNotes: RelatedItem[];
  /** Related pages */
  relatedPages: RelatedItem[];
  /** Code references */
  codeReferences: CodeReference[];
  /** Task checklist */
  tasksChecklist: TaskItem[];
  /** Generated Claude Code prompt */
  claudeCodePrompt: string;
  /** When context was generated */
  generatedAt: string;
  /** When context was last refined */
  lastRefinedAt?: string;
}

export interface AIContextProps {
  /** Issue ID */
  issueId: string;
  /** Issue identifier for display */
  issueIdentifier?: string;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function AIContextSkeleton() {
  return (
    <div className="space-y-6 p-4">
      <div className="space-y-3">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>

      <Separator />

      <div className="space-y-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>

      <Separator />

      <div className="space-y-3">
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
        <Skeleton className="h-12" />
      </div>
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

interface EmptyStateProps {
  onGenerate: () => void;
  isGenerating: boolean;
}

function EmptyState({ onGenerate, isGenerating }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Sparkles className="size-16 text-ai/30 mb-4" />
      <h3 className="text-lg font-medium mb-2">No AI Context Yet</h3>
      <p className="text-muted-foreground max-w-md mb-6">
        Generate AI-powered context to get related documentation, code references, implementation
        tasks, and a Claude Code prompt for this issue.
      </p>
      <Button onClick={onGenerate} disabled={isGenerating}>
        {isGenerating ? (
          <>
            <Loader2 className="size-4 mr-2 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="size-4 mr-2" />
            Generate Context
          </>
        )}
      </Button>
    </div>
  );
}

// ============================================================================
// Code References Section
// ============================================================================

interface CodeReferencesSectionProps {
  references: CodeReference[];
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

function CodeReferencesSection({
  references,
  collapsible = true,
  defaultCollapsed = false,
}: CodeReferencesSectionProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

  if (references.length === 0) return null;

  return (
    <div className="space-y-3">
      <button
        onClick={() => collapsible && setIsCollapsed(!isCollapsed)}
        className="flex items-center gap-2 w-full text-left"
        disabled={!collapsible}
      >
        <Code className="size-4 text-purple-600 dark:text-purple-400" />
        <span className="text-sm font-medium">Code References</span>
        <Badge variant="secondary" className="text-xs">
          {references.length}
        </Badge>
      </button>

      {!isCollapsed && (
        <div className="space-y-2 pl-6">
          {references
            .sort((a, b) => b.relevance - a.relevance)
            .map((ref) => (
              <div key={ref.id} className="rounded-lg border bg-slate-950 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-900">
                  <span className="text-xs text-slate-400 font-mono truncate">
                    {ref.filePath}:{ref.lineStart}-{ref.lineEnd}
                  </span>
                  <Badge variant="outline" className="text-xs text-slate-400">
                    {Math.round(ref.relevance * 100)}%
                  </Badge>
                </div>
                <pre className="p-3 overflow-x-auto text-xs font-mono text-slate-300 max-h-[200px]">
                  <code>{ref.content}</code>
                </pre>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Context Header
// ============================================================================

interface ContextHeaderProps {
  generatedAt?: string;
  lastRefinedAt?: string;
  onRegenerate: () => void;
  onExport: () => void;
  isRegenerating: boolean;
  isExporting: boolean;
}

function ContextHeader({
  generatedAt,
  lastRefinedAt,
  onRegenerate,
  onExport,
  isRegenerating,
  isExporting,
}: ContextHeaderProps) {
  const displayDate = lastRefinedAt || generatedAt;

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Clock className="size-4" />
        {displayDate && (
          <span>
            {lastRefinedAt ? 'Last refined' : 'Generated'} {new Date(displayDate).toLocaleString()}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onExport} disabled={isExporting}>
          {isExporting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Download className="size-4" />
          )}
          <span className="ml-1.5">Export</span>
        </Button>

        <Button variant="outline" size="sm" onClick={onRegenerate} disabled={isRegenerating}>
          {isRegenerating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <RefreshCw className="size-4" />
          )}
          <span className="ml-1.5">Regenerate</span>
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const AIContext = observer(function AIContext({
  issueId,
  issueIdentifier,
  className,
}: AIContextProps) {
  // Hooks
  const {
    data: contextData,
    isLoading,
    error,
    generate,
    isGenerating,
    regenerate,
    isRegenerating,
    updateTask,
  } = useAIContext(issueId);

  const { messages, suggestedQuestions, isTyping, sendMessage, clearConversation } =
    useAIContextChat(issueId);

  const { exportAsMarkdown, isExporting } = useExportContext(issueId);

  // Loading state
  if (isLoading) {
    return <AIContextSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12', className)}>
        <AlertCircle className="size-12 text-destructive mb-4" />
        <p className="text-muted-foreground">Failed to load AI context</p>
        <p className="text-xs text-muted-foreground mt-1">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={generate}>
          Try Again
        </Button>
      </div>
    );
  }

  // Empty state
  if (!contextData) {
    return (
      <div className={className}>
        <EmptyState onGenerate={generate} isGenerating={isGenerating} />
      </div>
    );
  }

  // Combine related items for ContextItemList
  const allRelatedItems: RelatedItem[] = [
    ...contextData.relatedIssues,
    ...contextData.relatedNotes,
    ...contextData.relatedPages,
  ];

  return (
    <ScrollArea className={cn('h-full', className)}>
      <div className="space-y-6 p-4">
        {/* Header */}
        <ContextHeader
          generatedAt={contextData.generatedAt}
          lastRefinedAt={contextData.lastRefinedAt}
          onRegenerate={regenerate}
          onExport={exportAsMarkdown}
          isRegenerating={isRegenerating}
          isExporting={isExporting}
        />

        {/* Summary */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <FileText className="size-4 text-blue-600 dark:text-blue-400" />
            <h3 className="text-sm font-medium">Summary</h3>
          </div>
          <p className="text-sm text-muted-foreground pl-6">{contextData.summary}</p>
        </div>

        <Separator />

        {/* Related Items */}
        {allRelatedItems.length > 0 && (
          <>
            <ContextItemList
              title="Related Issues"
              items={allRelatedItems}
              type="issue"
              maxDisplay={5}
            />

            <ContextItemList
              title="Related Notes"
              items={allRelatedItems}
              type="note"
              maxDisplay={5}
            />

            <ContextItemList
              title="Related Pages"
              items={allRelatedItems}
              type="page"
              maxDisplay={5}
            />

            <Separator />
          </>
        )}

        {/* Code References */}
        {contextData.codeReferences.length > 0 && (
          <>
            <CodeReferencesSection references={contextData.codeReferences} />
            <Separator />
          </>
        )}

        {/* Tasks */}
        {contextData.tasksChecklist.length > 0 && (
          <>
            <TaskChecklist
              tasks={contextData.tasksChecklist}
              onTaskToggle={(taskId, completed) => updateTask(taskId, { completed })}
              collapsible
            />
            <Separator />
          </>
        )}

        {/* Claude Code Prompt */}
        {contextData.claudeCodePrompt && (
          <>
            <ClaudeCodePrompt
              prompt={contextData.claudeCodePrompt}
              issueIdentifier={issueIdentifier}
              collapsible
            />
            <Separator />
          </>
        )}

        {/* Chat */}
        <ContextChat
          issueId={issueId}
          messages={messages}
          suggestedQuestions={suggestedQuestions}
          isTyping={isTyping}
          onSendMessage={sendMessage}
          onClearConversation={clearConversation}
          collapsible
          defaultCollapsed={messages.length === 0}
        />
      </div>
    </ScrollArea>
  );
});

export default AIContext;
