'use client';

import * as React from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { copyToClipboard } from '@/lib/copy-context';
import { useCopyFeedback } from '@/features/issues/hooks/use-copy-feedback';
import type { ContextPrompt } from '@/stores/ai/AIContextStore';

export interface PromptBlockProps {
  prompt: ContextPrompt;
  defaultExpanded?: boolean;
}

export function PromptBlock({ prompt, defaultExpanded }: PromptBlockProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded ?? false);
  const { copied, handleCopy } = useCopyFeedback();
  const contentId = `prompt-content-${prompt.taskId}`;

  const onCopyClick = () => {
    void handleCopy(() => copyToClipboard(prompt.content));
  };

  const toggle = () => setIsExpanded((prev) => !prev);

  const Chevron = isExpanded ? ChevronDown : ChevronRight;

  return (
    <div className="rounded-md border border-border">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={isExpanded}
          aria-controls={contentId}
          className={cn(
            'flex flex-1 items-center gap-2 text-left text-sm font-medium min-w-0',
            'hover:text-foreground transition-colors'
          )}
        >
          <Chevron className="h-4 w-4 shrink-0 text-foreground-muted" />
          <span className="flex-1 truncate">{prompt.title}</span>
        </button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onCopyClick}
          aria-label={copied ? 'Copied to clipboard' : 'Copy prompt to clipboard'}
          className="h-7 gap-1.5 px-2 text-xs shrink-0"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              Copy
            </>
          )}
        </Button>
      </div>

      {isExpanded && (
        <div id={contentId} className="px-3 pb-3">
          <pre className="bg-muted rounded-md p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap">
            {prompt.content}
          </pre>
        </div>
      )}
    </div>
  );
}
