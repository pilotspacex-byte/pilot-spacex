'use client';

/**
 * AIContextPanel - Main container for AI context generation and display.
 *
 * T132: Shows streaming progress, Claude Code prompt, and related items.
 * Integrates with AIContextStore for state management.
 *
 * @example
 * ```tsx
 * <AIContextPanel issueId={issueId} />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useStore } from '@/stores';
import { AIContextStreaming } from './ai-context-streaming';
import { ClaudeCodePromptCard } from './claude-code-prompt-card';
import { RelatedItemsList, type RelatedItem } from './related-items-list';

// ============================================================================
// Types
// ============================================================================

export interface AIContextPanelProps {
  /** Issue ID to generate context for */
  issueId: string;
  /** Additional class name */
  className?: string;
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
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      <Sparkles className="size-16 text-ai/30 mb-4" />
      <h3 className="text-lg font-medium mb-2">No AI Context Yet</h3>
      <p className="text-muted-foreground max-w-md mb-6 text-sm">
        Generate AI-powered context to get related documentation, code references, similar issues,
        and a Claude Code prompt for implementation guidance.
      </p>
      <Button onClick={onGenerate} disabled={isGenerating} variant="default" size="lg">
        {isGenerating ? (
          <>
            <Sparkles className="size-4 mr-2 animate-pulse" />
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
// Error State
// ============================================================================

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
}

function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
      <AlertCircle className="size-12 text-destructive mb-4" />
      <h3 className="text-lg font-medium mb-2">Failed to Generate Context</h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-md">{error}</p>
      <Button onClick={onRetry} variant="outline">
        <RefreshCw className="size-4 mr-2" />
        Try Again
      </Button>
    </div>
  );
}

// ============================================================================
// Results Display
// ============================================================================

interface ResultsProps {
  claudeCodePrompt: string;
  relatedDocs: string[];
  relatedCode: string[];
  similarIssues: string[];
  onRefresh: () => void;
}

function Results({
  claudeCodePrompt,
  relatedDocs,
  relatedCode,
  similarIssues,
  onRefresh,
}: ResultsProps) {
  // Transform string arrays to RelatedItem format
  const docsItems: RelatedItem[] = React.useMemo(
    () => relatedDocs.map((doc) => ({ title: doc })),
    [relatedDocs]
  );

  const codeItems: RelatedItem[] = React.useMemo(
    () => relatedCode.map((code) => ({ title: code })),
    [relatedCode]
  );

  const issueItems: RelatedItem[] = React.useMemo(
    () => similarIssues.map((issue) => ({ title: issue })),
    [similarIssues]
  );

  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-6">
        {/* Header with refresh button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-ai" />
            <h2 className="text-lg font-semibold">AI Context</h2>
          </div>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="size-4 mr-2" />
            Refresh
          </Button>
        </div>

        <Separator />

        {/* Claude Code Prompt */}
        {claudeCodePrompt && (
          <>
            <ClaudeCodePromptCard prompt={claudeCodePrompt} />
            <Separator />
          </>
        )}

        {/* Related Documents */}
        {docsItems.length > 0 && (
          <>
            <RelatedItemsList
              title="Related Documents"
              items={docsItems}
              type="doc"
              maxDisplay={5}
            />
            <Separator />
          </>
        )}

        {/* Related Code */}
        {codeItems.length > 0 && (
          <>
            <RelatedItemsList title="Related Code" items={codeItems} type="code" maxDisplay={5} />
            <Separator />
          </>
        )}

        {/* Similar Issues */}
        {issueItems.length > 0 && (
          <>
            <RelatedItemsList
              title="Similar Issues"
              items={issueItems}
              type="issue"
              maxDisplay={5}
            />
          </>
        )}

        {/* Empty state if no results */}
        {!claudeCodePrompt &&
          docsItems.length === 0 &&
          codeItems.length === 0 &&
          issueItems.length === 0 && (
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">
                No context generated. Try refreshing to generate new context.
              </p>
            </div>
          )}
      </div>
    </ScrollArea>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const AIContextPanel = observer(function AIContextPanel({
  issueId,
  className,
}: AIContextPanelProps) {
  const { aiStore } = useStore();

  // Generate context on mount if not already loading or has result
  React.useEffect(() => {
    if (
      !aiStore.aiContext.isLoading &&
      !aiStore.aiContext.result &&
      aiStore.aiContext.currentIssueId !== issueId
    ) {
      aiStore.aiContext.generateContext(issueId);
    }
  }, [issueId, aiStore.aiContext]);

  const handleGenerate = () => {
    aiStore.aiContext.generateContext(issueId);
  };

  const handleRefresh = () => {
    aiStore.aiContext.clearCache(issueId);
    aiStore.aiContext.generateContext(issueId);
  };

  // Loading state - show streaming progress
  if (aiStore.aiContext.isLoading) {
    return (
      <div className={className}>
        <AIContextStreaming phases={aiStore.aiContext.phases} />
      </div>
    );
  }

  // Error state
  if (aiStore.aiContext.error) {
    return (
      <div className={className}>
        <ErrorState error={aiStore.aiContext.error} onRetry={handleGenerate} />
      </div>
    );
  }

  // Results state
  if (aiStore.aiContext.result) {
    return (
      <div className={cn('h-full', className)}>
        <Results
          claudeCodePrompt={aiStore.aiContext.result.claudeCodePrompt}
          relatedDocs={aiStore.aiContext.result.relatedDocs_legacy}
          relatedCode={aiStore.aiContext.result.relatedCode}
          similarIssues={aiStore.aiContext.result.similarIssues}
          onRefresh={handleRefresh}
        />
      </div>
    );
  }

  // Empty state - no context generated yet
  return (
    <div className={className}>
      <EmptyState onGenerate={handleGenerate} isGenerating={aiStore.aiContext.isLoading} />
    </div>
  );
});

export default AIContextPanel;
