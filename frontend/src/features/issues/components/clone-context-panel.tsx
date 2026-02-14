'use client';

import * as React from 'react';
import { Terminal, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export type ExportFormat = 'markdown' | 'claude_code' | 'task_list';

export interface CloneContextPanelProps {
  onExport: (format: ExportFormat) => Promise<string | null>;
  isLoading?: boolean;
  stats?: {
    tasksCount: number;
    relatedIssuesCount: number;
    relatedDocsCount: number;
  };
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

const FORMAT_LABELS: Record<ExportFormat, string> = {
  markdown: 'Markdown',
  claude_code: 'Claude Code',
  task_list: 'Task List',
};

const COPY_FEEDBACK_MS = 1500;

// ============================================================================
// Component
// ============================================================================

export function CloneContextPanel({
  onExport,
  isLoading,
  stats,
  className,
}: CloneContextPanelProps) {
  const [activeFormat, setActiveFormat] = React.useState<ExportFormat>('markdown');
  const [preview, setPreview] = React.useState<string>('');
  const [isCopied, setIsCopied] = React.useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(false);

  const copyTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>(undefined);

  // Clean up timeout on unmount
  React.useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    };
  }, []);

  const loadPreview = React.useCallback(
    async (format: ExportFormat) => {
      setIsLoadingPreview(true);
      try {
        const content = await onExport(format);
        setPreview(content ?? '');
      } catch {
        setPreview('Failed to load preview.');
      } finally {
        setIsLoadingPreview(false);
      }
    },
    [onExport]
  );

  // Load preview when popover opens or format changes
  React.useEffect(() => {
    if (isOpen) {
      void loadPreview(activeFormat);
    }
  }, [isOpen, activeFormat, loadPreview]);

  const handleCopy = async () => {
    if (!preview || isLoadingPreview) return;

    try {
      await navigator.clipboard.writeText(preview);
      setIsCopied(true);
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setIsCopied(false), COPY_FEEDBACK_MS);
    } catch {
      // Fallback for environments where clipboard API is unavailable
      const textarea = document.createElement('textarea');
      textarea.value = preview;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setIsCopied(true);
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      copyTimeoutRef.current = setTimeout(() => setIsCopied(false), COPY_FEEDBACK_MS);
    }
  };

  const handleTabChange = (value: string) => {
    setActiveFormat(value as ExportFormat);
    setIsCopied(false);
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-1.5', className)}
          disabled={isLoading}
          aria-haspopup="dialog"
        >
          <Terminal className="size-4" aria-hidden="true" />
          Clone Context
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[420px] p-0" align="end" sideOffset={8} id="clone-context-panel">
        <Tabs value={activeFormat} onValueChange={handleTabChange}>
          <div className="border-b px-3 pt-3 pb-0">
            <TabsList className="w-full">
              <TabsTrigger value="markdown" className="flex-1 text-xs">
                Markdown
              </TabsTrigger>
              <TabsTrigger value="claude_code" className="flex-1 text-xs">
                Claude Code
              </TabsTrigger>
              <TabsTrigger value="task_list" className="flex-1 text-xs">
                Task List
              </TabsTrigger>
            </TabsList>
          </div>

          {(['markdown', 'claude_code', 'task_list'] as const).map((format) => (
            <TabsContent key={format} value={format} className="mt-0">
              <div className="relative">
                <pre
                  className="max-h-[300px] overflow-auto bg-[#1E1E1E] text-[#D4D4D4] p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap"
                  role="region"
                  aria-label={`${FORMAT_LABELS[format]} preview`}
                >
                  {isLoadingPreview ? (
                    <span className="text-muted-foreground animate-pulse">Loading preview...</span>
                  ) : (
                    preview || 'No content available'
                  )}
                </pre>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  disabled={!preview || isLoadingPreview}
                  className={cn(
                    'absolute top-2 right-2 h-7 px-2 text-xs',
                    isCopied
                      ? 'text-green-400 hover:text-green-400'
                      : 'text-[#D4D4D4] hover:text-white hover:bg-[#333]'
                  )}
                  aria-live="polite"
                  aria-label={isCopied ? 'Context copied to clipboard' : 'Copy context'}
                >
                  {isCopied ? (
                    <>
                      <Check className="size-3.5 mr-1" aria-hidden="true" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5 mr-1" aria-hidden="true" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </TabsContent>
          ))}
        </Tabs>

        {stats && (
          <div className="border-t px-4 py-2.5 text-xs text-muted-foreground">
            Includes: {stats.tasksCount} tasks, {stats.relatedIssuesCount} issues,{' '}
            {stats.relatedDocsCount} docs
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
