'use client';

/**
 * ClaudeCodePrompt - Display formatted Claude Code prompt with copy functionality.
 *
 * T214: Shows formatted prompt in code block with syntax highlighting,
 * copy to clipboard, and edit before copy option.
 */

import * as React from 'react';
import { Copy, Check, Edit2, X, ChevronDown, ChevronRight, Terminal, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// ============================================================================
// Types
// ============================================================================

export interface ClaudeCodePromptProps {
  /** The generated prompt text */
  prompt: string;
  /** Issue identifier for display */
  issueIdentifier?: string;
  /** Whether the section is collapsible */
  collapsible?: boolean;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Maximum visible height before scrolling */
  maxHeight?: number;
  /** Called when prompt is copied */
  onCopy?: () => void;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Syntax Highlighting (Simple)
// ============================================================================

function highlightPrompt(text: string): React.ReactNode {
  // Split into lines and highlight certain patterns
  const lines = text.split('\n');

  return lines.map((line, i) => {
    let highlighted: React.ReactNode = line;

    // Highlight headings (## or #)
    if (line.startsWith('##') || line.startsWith('#')) {
      highlighted = <span className="text-blue-400 font-semibold">{line}</span>;
    }
    // Highlight code blocks markers
    else if (line.startsWith('```')) {
      highlighted = <span className="text-purple-400">{line}</span>;
    }
    // Highlight bullet points
    else if (line.trimStart().startsWith('-') || line.trimStart().startsWith('*')) {
      const indent = line.length - line.trimStart().length;
      const bullet = line.trimStart().charAt(0);
      const rest = line.trimStart().slice(1);
      highlighted = (
        <>
          {' '.repeat(indent)}
          <span className="text-yellow-400">{bullet}</span>
          {rest}
        </>
      );
    }
    // Highlight file paths
    else if (
      line.includes('/') &&
      (line.includes('.ts') || line.includes('.tsx') || line.includes('.py'))
    ) {
      highlighted = <span className="text-green-400">{line}</span>;
    }
    // Highlight important keywords
    else if (line.toLowerCase().includes('important') || line.toLowerCase().includes('note:')) {
      highlighted = <span className="text-orange-400">{line}</span>;
    }

    return (
      <React.Fragment key={i}>
        {highlighted}
        {i < lines.length - 1 && '\n'}
      </React.Fragment>
    );
  });
}

// ============================================================================
// Instructions Card
// ============================================================================

function UsageInstructions() {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20">
      <div className="flex items-start gap-2">
        <Info className="size-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
          <p className="font-medium">How to use with Claude Code:</p>
          <ol className="list-decimal list-inside space-y-0.5 text-blue-600 dark:text-blue-400">
            <li>Copy the prompt above</li>
            <li>Open Claude Code in your terminal</li>
            <li>Paste the prompt and press Enter</li>
            <li>Claude will analyze your codebase and implement the task</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ClaudeCodePrompt({
  prompt,
  issueIdentifier,
  collapsible = true,
  defaultCollapsed = false,
  maxHeight = 400,
  onCopy,
  className,
}: ClaudeCodePromptProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [isCopied, setIsCopied] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editedPrompt, setEditedPrompt] = React.useState(prompt);

  // Reset edited prompt when original changes
  React.useEffect(() => {
    setEditedPrompt(prompt);
  }, [prompt]);

  const handleCopy = async (textToCopy: string) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setIsCopied(true);
      onCopy?.();
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleCopyAndClose = async () => {
    await handleCopy(editedPrompt);
    setIsEditing(false);
  };

  if (!prompt) {
    return null;
  }

  const header = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {collapsible &&
          (isCollapsed ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />)}
        <Terminal className="size-4 text-ai" />
        <span className="text-sm font-medium">Claude Code Prompt</span>
        {issueIdentifier && (
          <Badge variant="outline" className="text-xs">
            {issueIdentifier}
          </Badge>
        )}
      </div>

      {!isCollapsed && (
        <div className="flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
                >
                  <Edit2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit before copy</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <Button
            variant={isCopied ? 'default' : 'outline'}
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleCopy(prompt);
            }}
            className={cn(isCopied && 'bg-green-600 hover:bg-green-600')}
          >
            {isCopied ? (
              <>
                <Check className="size-4 mr-1" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="size-4 mr-1" />
                Copy
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );

  const content = (
    <div className="space-y-3 mt-3">
      {/* Prompt code block */}
      <div className="rounded-lg border bg-slate-950 overflow-hidden" style={{ maxHeight }}>
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800 bg-slate-900">
          <span className="text-xs text-slate-400">prompt.md</span>
          <span className="text-xs text-slate-500">{prompt.length} chars</span>
        </div>
        <pre
          className="p-4 overflow-auto text-sm font-mono text-slate-300 whitespace-pre-wrap"
          style={{ maxHeight: maxHeight - 50 }}
        >
          <code>{highlightPrompt(prompt)}</code>
        </pre>
      </div>

      {/* Usage instructions */}
      <UsageInstructions />
    </div>
  );

  const mainContent = collapsible ? (
    <Collapsible
      open={!isCollapsed}
      onOpenChange={(open) => setIsCollapsed(!open)}
      className={className}
    >
      <CollapsibleTrigger className="w-full text-left">{header}</CollapsibleTrigger>
      <CollapsibleContent>{content}</CollapsibleContent>
    </Collapsible>
  ) : (
    <div className={className}>
      {header}
      {content}
    </div>
  );

  return (
    <>
      {mainContent}

      {/* Edit Dialog */}
      <Dialog open={isEditing} onOpenChange={setIsEditing}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Edit Prompt</DialogTitle>
            <DialogDescription>
              Customize the prompt before copying to Claude Code
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <Textarea
              value={editedPrompt}
              onChange={(e) => setEditedPrompt(e.target.value)}
              className="min-h-[400px] font-mono text-sm"
              placeholder="Enter your prompt..."
            />

            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{editedPrompt.length} characters</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditedPrompt(prompt)}
                disabled={editedPrompt === prompt}
              >
                Reset to original
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditing(false)}>
              <X className="size-4 mr-1" />
              Cancel
            </Button>
            <Button onClick={handleCopyAndClose}>
              <Copy className="size-4 mr-1" />
              Copy & Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default ClaudeCodePrompt;
