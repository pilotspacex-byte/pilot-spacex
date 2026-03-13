'use client';

import * as React from 'react';
import {
  TerminalSquare,
  Copy,
  Check,
  ListChecks,
  MessageSquare,
  FileText,
  FileQuestion,
  Network,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export type ExportFormat = 'markdown' | 'claude_code' | 'task_list' | 'implementation_plan';

export interface CloneContextPanelProps {
  onExport: (format: ExportFormat) => Promise<string | null>;
  isLoading?: boolean;
  issueIdentifier?: string;
  issueTitle?: string;
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

interface TabConfig {
  format: ExportFormat;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const TABS: TabConfig[] = [
  {
    format: 'claude_code',
    label: 'Prompt',
    icon: <MessageSquare className="size-3.5" aria-hidden="true" />,
    description: 'Conversational prompt — paste into Claude Code chat',
  },
  {
    format: 'markdown',
    label: 'Markdown',
    icon: <FileText className="size-3.5" aria-hidden="true" />,
    description: 'Structured context — works in any markdown-compatible tool',
  },
  {
    format: 'task_list',
    label: 'Checklist',
    icon: <ListChecks className="size-3.5" aria-hidden="true" />,
    description: 'Step-by-step task list with acceptance criteria',
  },
  {
    format: 'implementation_plan',
    label: 'Plan',
    icon: <Network className="size-3.5" aria-hidden="true" />,
    description: 'Orchestrator-mode plan with subagents for Claude Code',
  },
];

const COPY_FEEDBACK_MS = 2000;

// ============================================================================
// Loading skeleton
// ============================================================================

function CodeSkeleton() {
  return (
    <div className="space-y-2 p-4" aria-busy="true" aria-label="Loading context...">
      {[100, 85, 92, 60].map((w, i) => (
        <div
          key={i}
          className="h-3 rounded bg-neutral-700/60 animate-pulse"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}

// ============================================================================
// Empty state
// ============================================================================

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <FileQuestion className="size-8 text-neutral-500 mb-3" aria-hidden="true" />
      <p className="text-sm font-medium text-neutral-300">No context to clone</p>
      <p className="text-xs text-neutral-500 mt-1">
        Add a description, tasks, or linked issues to generate context.
      </p>
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function CloneContextPanel({
  onExport,
  isLoading,
  issueIdentifier,
  issueTitle,
  stats,
  className,
}: CloneContextPanelProps) {
  const [activeFormat, setActiveFormat] = React.useState<ExportFormat>('claude_code');
  const [preview, setPreview] = React.useState<string>('');
  const [isCopied, setIsCopied] = React.useState(false);
  const [isLoadingPreview, setIsLoadingPreview] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(false);

  const copyTimeoutRef = React.useRef<ReturnType<typeof setTimeout>>(undefined);
  const triggerRef = React.useRef<HTMLButtonElement>(null);

  React.useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    };
  }, []);

  const loadPreview = React.useCallback(
    async (format: ExportFormat) => {
      setIsLoadingPreview(true);
      setPreview('');
      try {
        const content = await onExport(format);
        setPreview(content ?? '');
      } catch {
        setPreview('');
      } finally {
        setIsLoadingPreview(false);
      }
    },
    [onExport]
  );

  React.useEffect(() => {
    if (isOpen) {
      void loadPreview(activeFormat);
    }
  }, [isOpen, activeFormat, loadPreview]);

  // ⌘C / Ctrl+C when panel is open and no text is selected
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta || e.key !== 'c') return;
      const selection = window.getSelection();
      if (selection && selection.toString().length > 0) return; // user is selecting text
      e.preventDefault();
      void handleCopy();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, preview]);

  const copyText = React.useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(textarea);
      textarea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (!success) {
        throw new Error('execCommand copy failed');
      }
    }
  }, []);

  const handleCopy = React.useCallback(async () => {
    if (!preview || isLoadingPreview) return;
    await copyText(preview);
    setIsCopied(true);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setIsCopied(false), COPY_FEEDBACK_MS);
  }, [preview, isLoadingPreview, copyText]);

  const handleCopyAndClose = async () => {
    await handleCopy();
    setIsOpen(false);
  };

  const handleTabChange = (format: ExportFormat) => {
    setActiveFormat(format);
    setIsCopied(false);
  };

  // ArrowLeft / ArrowRight keyboard navigation for segmented control
  const handleSegmentKeyDown = (e: React.KeyboardEvent) => {
    const idx = TABS.findIndex((t) => t.format === activeFormat);
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      const next = TABS[(idx + 1) % TABS.length];
      if (next) handleTabChange(next.format);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      const prev = TABS[(idx - 1 + TABS.length) % TABS.length];
      if (prev) handleTabChange(prev.format);
    }
  };

  const activeTab = TABS.find((t) => t.format === activeFormat) ?? TABS[0]!;
  const statsLine = stats
    ? `${stats.tasksCount} tasks · ${stats.relatedIssuesCount} issues · ${stats.relatedDocsCount} docs`
    : null;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              ref={triggerRef}
              variant="ghost"
              size="sm"
              className={cn(
                'gap-1.5 h-8 px-2.5 text-xs font-medium text-muted-foreground',
                'transition-colors',
                isOpen && 'bg-[#6B8FAD]/10 text-[#6B8FAD]',
                className
              )}
              disabled={isLoading}
              aria-haspopup="dialog"
              aria-expanded={isOpen}
            >
              <TerminalSquare
                className={cn('size-4', isOpen ? 'text-[#6B8FAD]' : 'text-muted-foreground')}
                aria-hidden="true"
              />
              <span>Clone</span>
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent side="bottom">Clone context for Claude Code</TooltipContent>
      </Tooltip>

      <PopoverContent
        className="w-[440px] p-0 overflow-hidden"
        align="end"
        sideOffset={8}
        role="dialog"
        aria-label="Clone context for Claude Code"
        onOpenAutoFocus={(e) => {
          e.preventDefault();
          // Focus the first tab button
        }}
        onCloseAutoFocus={(e) => {
          e.preventDefault();
          triggerRef.current?.focus();
        }}
      >
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* ── Header ── */}
              <div className="flex items-center h-12 border-b border-border px-4">
                <TerminalSquare
                  className="size-4 text-[#6B8FAD] mr-2 shrink-0"
                  aria-hidden="true"
                />
                <span className="text-sm font-semibold text-foreground flex-1">Clone Context</span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setIsOpen(false)}
                  className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  aria-label="Close panel"
                >
                  <X className="size-4" />
                </Button>
              </div>

              {/* ── Context summary ── */}
              {(issueIdentifier || issueTitle || statsLine) && (
                <div className="px-4 py-3 border-b border-border">
                  {(issueIdentifier || issueTitle) && (
                    <p className="text-sm font-medium text-foreground truncate">
                      {[issueIdentifier, issueTitle].filter(Boolean).join(' · ')}
                    </p>
                  )}
                  {statsLine && <p className="text-xs text-muted-foreground mt-0.5">{statsLine}</p>}
                </div>
              )}

              {/* ── Segmented control (tabs) ── */}
              <div className="px-4 pt-3 pb-0">
                <div
                  className="inline-flex w-full rounded-lg bg-muted/50 p-1"
                  role="tablist"
                  aria-label="Export format"
                  onKeyDown={handleSegmentKeyDown}
                >
                  {TABS.map((tab) => (
                    <button
                      key={tab.format}
                      role="tab"
                      aria-selected={activeFormat === tab.format}
                      aria-controls={`panel-${tab.format}`}
                      onClick={() => handleTabChange(tab.format)}
                      className={cn(
                        'flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        activeFormat === tab.format
                          ? 'bg-background text-foreground shadow-sm font-semibold'
                          : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      {tab.icon}
                      {tab.label}
                    </button>
                  ))}
                </div>
                {/* Tab description */}
                <p className="text-[11px] text-muted-foreground px-0.5 py-2">
                  {activeTab.description}
                </p>
              </div>

              {/* ── Code preview ── */}
              <div className="mx-3 mb-3 rounded-lg overflow-hidden border border-border relative">
                <div
                  id={`panel-${activeFormat}`}
                  role="tabpanel"
                  aria-label={`${activeTab.label} preview`}
                  className="bg-neutral-900 max-h-[280px] overflow-auto scrollbar-thin scrollbar-track-neutral-800 scrollbar-thumb-neutral-600"
                >
                  {isLoadingPreview ? (
                    <CodeSkeleton />
                  ) : preview ? (
                    <pre className="p-4 text-[13px] leading-5 font-mono text-neutral-200 whitespace-pre-wrap break-words">
                      {preview}
                    </pre>
                  ) : (
                    <EmptyState />
                  )}
                </div>

                {/* Scroll shadow overlay */}
                {preview && !isLoadingPreview && (
                  <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-neutral-900 to-transparent pointer-events-none" />
                )}

                {/* Inline copy button */}
                {preview && !isLoadingPreview && (
                  <button
                    onClick={handleCopy}
                    className={cn(
                      'absolute top-2 right-2 flex items-center gap-1 h-8 px-2.5 rounded-md text-xs font-medium',
                      'border transition-all duration-150',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      isCopied
                        ? 'text-[#29A386] bg-[#29A386]/20 border-[#29A386]/30'
                        : 'text-neutral-300 bg-neutral-800 border-neutral-700 hover:bg-neutral-700 hover:text-neutral-100'
                    )}
                    aria-label={isCopied ? 'Copied to clipboard' : 'Copy context to clipboard'}
                  >
                    {isCopied ? (
                      <>
                        <Check className="size-3.5" aria-hidden="true" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="size-3.5" aria-hidden="true" />
                        Copy
                      </>
                    )}
                  </button>
                )}

                {/* aria-live region for copy announcement */}
                <div aria-live="polite" className="sr-only">
                  {isCopied ? 'Copied to clipboard' : ''}
                </div>
              </div>

              {/* ── Footer ── */}
              <div className="border-t border-border px-4 py-3 flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground font-mono">
                  {typeof navigator !== 'undefined' && /Mac/.test(navigator.platform)
                    ? '⌘C to copy'
                    : 'Ctrl+C to copy'}
                </span>
                <Button
                  size="sm"
                  onClick={() => void handleCopyAndClose()}
                  disabled={!preview || isLoadingPreview}
                  className="h-7 px-3 text-xs"
                >
                  Copy &amp; Close
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </PopoverContent>
    </Popover>
  );
}

// Re-export for legacy usage in AIContextTab (stats prop still accepted, displayed as context summary)
export default CloneContextPanel;
