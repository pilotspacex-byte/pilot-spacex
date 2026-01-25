/**
 * useExportContext - Hook for exporting AI context as markdown.
 *
 * T215: Provides markdown export functionality with download.
 */

import * as React from 'react';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import type { AIContextData } from '@/components/issues/AIContext';

// ============================================================================
// Types
// ============================================================================

interface ExportResponse {
  markdown: string;
  filename: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function generateMarkdownFromContext(context: AIContextData, issueId: string): string {
  const lines: string[] = [];

  lines.push(`# AI Context for Issue ${issueId}`);
  lines.push('');
  lines.push(`Generated: ${new Date(context.generatedAt).toLocaleString()}`);
  if (context.lastRefinedAt) {
    lines.push(`Last refined: ${new Date(context.lastRefinedAt).toLocaleString()}`);
  }
  lines.push('');

  // Summary
  lines.push('## Summary');
  lines.push('');
  lines.push(context.summary);
  lines.push('');

  // Related Issues
  if (context.relatedIssues.length > 0) {
    lines.push('## Related Issues');
    lines.push('');
    context.relatedIssues.forEach((item) => {
      lines.push(
        `- **${item.identifier || item.id}**: ${item.title} (${Math.round(item.relevance * 100)}% relevance)`
      );
      if (item.excerpt) {
        lines.push(`  > ${item.excerpt}`);
      }
    });
    lines.push('');
  }

  // Related Notes
  if (context.relatedNotes.length > 0) {
    lines.push('## Related Notes');
    lines.push('');
    context.relatedNotes.forEach((item) => {
      lines.push(`- **${item.title}** (${Math.round(item.relevance * 100)}% relevance)`);
      if (item.excerpt) {
        lines.push(`  > ${item.excerpt}`);
      }
    });
    lines.push('');
  }

  // Related Pages
  if (context.relatedPages.length > 0) {
    lines.push('## Related Pages');
    lines.push('');
    context.relatedPages.forEach((item) => {
      lines.push(`- **${item.title}** (${Math.round(item.relevance * 100)}% relevance)`);
      if (item.excerpt) {
        lines.push(`  > ${item.excerpt}`);
      }
    });
    lines.push('');
  }

  // Code References
  if (context.codeReferences.length > 0) {
    lines.push('## Code References');
    lines.push('');
    context.codeReferences.forEach((ref) => {
      lines.push(`### ${ref.filePath}:${ref.lineStart}-${ref.lineEnd}`);
      lines.push(`Relevance: ${Math.round(ref.relevance * 100)}%`);
      lines.push('');
      lines.push('```' + (ref.language || ''));
      lines.push(ref.content);
      lines.push('```');
      lines.push('');
    });
  }

  // Tasks
  if (context.tasksChecklist.length > 0) {
    lines.push('## Implementation Tasks');
    lines.push('');
    context.tasksChecklist.forEach((task) => {
      const checkbox = task.completed ? '[x]' : '[ ]';
      const effort = `[${task.effort}]`;
      lines.push(`- ${checkbox} ${task.title} ${effort}`);
      if (task.description) {
        lines.push(`  ${task.description}`);
      }
      if (task.dependsOn && task.dependsOn.length > 0) {
        lines.push(`  Dependencies: ${task.dependsOn.join(', ')}`);
      }
    });
    lines.push('');
  }

  // Claude Code Prompt
  if (context.claudeCodePrompt) {
    lines.push('## Claude Code Prompt');
    lines.push('');
    lines.push('```');
    lines.push(context.claudeCodePrompt);
    lines.push('```');
    lines.push('');
  }

  return lines.join('\n');
}

// ============================================================================
// Hook
// ============================================================================

export interface UseExportContextOptions {
  /** Issue identifier for filename */
  issueIdentifier?: string;
}

export interface UseExportContextReturn {
  /** Export as markdown file */
  exportAsMarkdown: () => void;
  /** Whether export is in progress */
  isExporting: boolean;
  /** Error from last export */
  error: Error | null;
}

export function useExportContext(
  issueId: string,
  options?: UseExportContextOptions
): UseExportContextReturn {
  const { issueIdentifier } = options ?? {};
  const [isExporting, setIsExporting] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);

  const exportAsMarkdown = React.useCallback(async () => {
    setIsExporting(true);
    setError(null);

    try {
      // Try to fetch from API first
      let markdown: string;
      let filename: string;

      try {
        const response = await apiClient.get<ExportResponse>(
          `/issues/${issueId}/ai-context/export`
        );
        markdown = response.markdown;
        filename = response.filename;
      } catch {
        // If API fails, try to generate from cached context
        const cachedContext = await apiClient.get<AIContextData>(`/issues/${issueId}/ai-context`);
        markdown = generateMarkdownFromContext(cachedContext, issueIdentifier || issueId);
        filename = `ai-context-${issueIdentifier || issueId}-${Date.now()}.md`;
      }

      downloadFile(markdown, filename, 'text/markdown');
      toast.success('Context exported', {
        description: `Downloaded ${filename}`,
      });
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error('Export failed');
      setError(errorObj);
      toast.error('Failed to export context', {
        description: errorObj.message,
      });
    } finally {
      setIsExporting(false);
    }
  }, [issueId, issueIdentifier]);

  return {
    exportAsMarkdown,
    isExporting,
    error,
  };
}

export default useExportContext;
