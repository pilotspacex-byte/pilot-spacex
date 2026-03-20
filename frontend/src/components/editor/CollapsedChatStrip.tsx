'use client';

/**
 * CollapsedChatStrip - Thin strip shown when the AI panel is collapsed.
 *
 * Desktop: vertical strip on right edge with "PilotSpace Agent" text.
 * Mobile: horizontal bar at bottom.
 */
import { ChevronLeft, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface CollapsedChatStripProps {
  onClick: () => void;
  className?: string;
}

export function CollapsedChatStrip({ onClick, className }: CollapsedChatStripProps) {
  return (
    <>
      {/* Desktop: Vertical strip on right edge */}
      <div
        className={cn(
          'hidden lg:flex flex-shrink-0 border-l border-ai-border/30 bg-ai-bg/30',
          className
        )}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClick}
              className="h-full w-10 rounded-none hover:bg-ai-muted/40 flex-col gap-2 py-4"
              data-testid="collapsed-chat-strip"
            >
              <ChevronLeft className="h-4 w-4 text-ai" />
              <span className="writing-mode-vertical text-[10px] font-medium text-ai">
                PilotSpace Agent
              </span>
              <MessageSquare className="h-4 w-4 text-ai mt-auto" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">Open PilotSpace Agent (⌘⇧P)</TooltipContent>
        </Tooltip>
      </div>

      {/* Mobile/Tablet: Horizontal bar at bottom */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-30 border-t border-border bg-background/90 backdrop-blur-sm">
        <Button
          variant="ghost"
          onClick={onClick}
          className="w-full h-10 rounded-none justify-between px-3 hover:bg-ai-muted/20"
          data-testid="collapsed-chat-strip-mobile"
        >
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-ai" />
            <span className="text-xs font-medium text-ai">PilotSpace Agent</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border bg-muted px-1 py-0.5 text-[9px] font-mono text-muted-foreground">
            ⌘⇧P
          </kbd>
        </Button>
      </div>
    </>
  );
}
