/**
 * ChatHeader - Compact chat title bar matching note-editor header height
 * Single line: [Bot Icon] · Title · [New] · [Close]
 */

import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Bot, X, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  title?: string;
  isStreaming?: boolean;
  onNewSession?: () => void;
  onClose?: () => void;
  className?: string;
}

export const ChatHeader = observer<ChatHeaderProps>(
  ({ title, isStreaming, onNewSession, onClose, className }) => {
    return (
      <div
        className={cn(
          'flex-shrink-0 bg-background/95 backdrop-blur-sm border-b border-border/50',
          'px-4',
          className
        )}
        data-testid="chat-header"
      >
        <div
          className={cn(
            'flex items-center text-muted-foreground',
            'gap-1.5 sm:gap-2',
            'text-[11px] sm:text-xs md:text-sm',
            'py-1 sm:py-1.5 md:py-2 lg:py-2.5'
          )}
        >
          {/* Bot icon + Title */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            <div className="flex items-center justify-center h-5 w-5 sm:h-6 sm:w-6 rounded-md bg-ai-muted flex-shrink-0">
              <Bot className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-ai" />
            </div>
            <span className="text-foreground font-medium truncate max-w-[100px] sm:max-w-[140px] md:max-w-[180px]">
              {title || 'PilotSpace Agent'}
            </span>
          </div>

          {/* Spacer */}
          <div className="flex-1 min-w-2" />

          {/* Action buttons */}
          <div className="flex items-center gap-0 sm:gap-0.5">
            {onNewSession && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onNewSession}
                    disabled={isStreaming}
                    className="h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                    data-testid="new-session-button"
                  >
                    <Plus className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>New session</TooltipContent>
              </Tooltip>
            )}

            {onClose && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onClose}
                    className="h-6 w-6 sm:h-7 sm:w-7 text-muted-foreground hover:text-foreground"
                    data-testid="close-chat-button"
                  >
                    <X className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Close chat</TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </div>
    );
  }
);

ChatHeader.displayName = 'ChatHeader';
