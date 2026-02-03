'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, RefreshCw, AlertCircle, Copy, Check, Link, CheckSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores';
import {
  generateFullContextMarkdown,
  generateSectionMarkdown,
  copyToClipboard,
} from '@/lib/copy-context';
import { useCopyFeedback } from '@/features/issues/hooks/use-copy-feedback';
import { AIContextStreaming } from './ai-context-streaming';
import { ContextSummaryCard } from './context-summary-card';
import { ContextSection } from './context-section';
import { RelatedIssuesSection } from './related-issues-section';
import { RelatedDocsSection } from './related-docs-section';
import { AITasksSection } from './ai-tasks-section';

export interface AIContextTabProps {
  issueId: string;
  className?: string;
}

export const AIContextTab = observer(function AIContextTab({
  issueId,
  className,
}: AIContextTabProps) {
  const { aiStore } = useStore();
  const contextStore = aiStore.aiContext;
  const { copied, handleCopy } = useCopyFeedback();

  // Auto-generate context on mount and when issueId changes.
  // Store handles cache hits, dedup, and issue switching internally.
  React.useEffect(() => {
    contextStore.generateContext(issueId);
  }, [issueId, contextStore]);

  const handleGenerate = () => {
    contextStore.generateContext(issueId);
  };

  const handleRegenerate = () => {
    contextStore.clearCache(issueId);
    contextStore.generateContext(issueId);
  };

  const handleCopyAll = () => {
    if (!contextStore.result) return;
    void handleCopy(() => copyToClipboard(generateFullContextMarkdown(contextStore.result!)));
  };

  const handleCopyRelated = async (): Promise<boolean> => {
    if (!contextStore.result) return false;
    const md =
      generateSectionMarkdown('related_issues', contextStore.result) +
      '\n\n' +
      generateSectionMarkdown('related_docs', contextStore.result);
    return copyToClipboard(md.trim());
  };

  const handleCopyTasks = async (): Promise<boolean> => {
    if (!contextStore.result) return false;
    const md =
      generateSectionMarkdown('tasks', contextStore.result) +
      '\n\n' +
      generateSectionMarkdown('prompts', contextStore.result);
    return copyToClipboard(md.trim());
  };

  // Combine related_issues and related_docs section errors
  const relatedSectionError =
    contextStore.sectionErrors.get('related_issues') ??
    contextStore.sectionErrors.get('related_docs') ??
    null;

  // Loading state
  if (contextStore.isLoading) {
    return (
      <div className={className} role="status" aria-live="polite">
        <AIContextStreaming phases={contextStore.phases} />
      </div>
    );
  }

  // Error state
  if (contextStore.error) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center py-12 px-6 text-center',
          className
        )}
        role="alert"
      >
        <AlertCircle className="size-12 text-destructive mb-4" aria-hidden="true" />
        <h3 className="text-lg font-medium mb-2">Failed to Generate Context</h3>
        <p className="text-muted-foreground text-sm mb-6 max-w-md">{contextStore.error}</p>
        <Button
          onClick={handleGenerate}
          variant="outline"
          aria-label="Try generating context again"
        >
          <RefreshCw className="size-4 mr-2" aria-hidden="true" />
          Try Again
        </Button>
      </div>
    );
  }

  // All sections failed — result exists but every section errored
  if (
    contextStore.result &&
    !contextStore.hasStructuredData &&
    contextStore.sectionErrors.size > 0
  ) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center py-12 px-6 text-center',
          className
        )}
        role="alert"
      >
        <AlertCircle className="size-12 text-destructive mb-4" aria-hidden="true" />
        <h3 className="text-lg font-medium mb-2">Partial Context Generation</h3>
        <p className="text-muted-foreground text-sm mb-6 max-w-md">
          Some sections failed to generate. Try regenerating for a complete result.
        </p>
        <Button onClick={handleRegenerate} variant="outline" aria-label="Regenerate AI context">
          <RefreshCw className="size-4 mr-2" aria-hidden="true" />
          Regenerate
        </Button>
      </div>
    );
  }

  // Results state - structured data
  if (contextStore.result && contextStore.hasStructuredData) {
    const hasRelatedData =
      contextStore.result.relatedIssues.length > 0 ||
      contextStore.result.relatedDocs.length > 0 ||
      relatedSectionError;
    const hasTasksData =
      contextStore.result.tasks.length > 0 ||
      contextStore.result.prompts.length > 0 ||
      contextStore.sectionErrors.get('tasks') ||
      contextStore.sectionErrors.get('prompts');

    return (
      <ScrollArea className={cn('h-full', className)}>
        <div className="space-y-6 p-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="size-5 text-ai" aria-hidden="true" />
              <h2 className="text-lg font-semibold">Full Context for AI Implementation</h2>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyAll}
                aria-label="Copy all context to clipboard"
              >
                {copied ? (
                  <Check className="size-4 mr-1.5" aria-hidden="true" />
                ) : (
                  <Copy className="size-4 mr-1.5" aria-hidden="true" />
                )}
                {copied ? 'Copied!' : 'Copy All'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerate}
                disabled={contextStore.isLoading}
                aria-label="Regenerate AI context"
              >
                <RefreshCw
                  className={cn(
                    'size-4 mr-1.5',
                    contextStore.isLoading && 'motion-safe:animate-spin'
                  )}
                  aria-hidden="true"
                />
                Regenerate
              </Button>
            </div>
          </div>

          <Separator />

          {/* Summary */}
          {contextStore.sectionErrors.get('summary') && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              <p>{contextStore.sectionErrors.get('summary')}</p>
            </div>
          )}
          {contextStore.result.summary && (
            <ContextSummaryCard summary={contextStore.result.summary} />
          )}

          {/* Related Context — render only when data or error exists */}
          {hasRelatedData && (
            <>
              <Separator />
              <ContextSection
                icon={Link}
                title="Related Context"
                onCopy={handleCopyRelated}
                error={relatedSectionError}
              >
                <div className="space-y-4">
                  <RelatedIssuesSection items={contextStore.result.relatedIssues} />
                  <RelatedDocsSection items={contextStore.result.relatedDocs} />
                </div>
              </ContextSection>
            </>
          )}

          {/* AI Tasks — render only when data or error exists */}
          {hasTasksData && (
            <>
              <Separator />
              <ContextSection
                icon={CheckSquare}
                title="AI Tasks"
                onCopy={handleCopyTasks}
                error={
                  contextStore.sectionErrors.get('tasks') ??
                  contextStore.sectionErrors.get('prompts') ??
                  null
                }
              >
                <AITasksSection
                  tasks={contextStore.result.tasks}
                  prompts={contextStore.result.prompts}
                />
              </ContextSection>
            </>
          )}
        </div>
      </ScrollArea>
    );
  }

  // Legacy fallback - result exists but no structured data
  if (contextStore.result) {
    return (
      <div className={cn('p-6 text-center text-sm text-muted-foreground', className)}>
        Context generated (legacy format). Regenerate for enhanced view.
      </div>
    );
  }

  // Empty state
  return (
    <div
      className={cn('flex flex-col items-center justify-center py-12 px-6 text-center', className)}
    >
      <Sparkles className="size-16 text-ai/40 mb-4" aria-hidden="true" />
      <h3 className="text-lg font-medium mb-2">No AI Context Yet</h3>
      <p className="text-muted-foreground max-w-md mb-6 text-sm">
        Generate AI-powered context to get related issues, documentation references, implementation
        tasks, and ready-to-use Claude Code prompts.
      </p>
      <Button onClick={handleGenerate} variant="default" size="lg" aria-label="Generate AI context">
        <Sparkles className="size-4 mr-2" aria-hidden="true" />
        Generate Context
      </Button>
    </div>
  );
});

export default AIContextTab;
