/**
 * OffScreenAIIndicator - Floating pill shown when AI edits a block off-screen.
 *
 * Positioned at bottom-center of the editor. Click scrolls to the block,
 * dismiss button closes the indicator.
 *
 * @module components/editor/OffScreenAIIndicator
 */

'use client';

import { memo } from 'react';
import { Sparkles, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface OffScreenAIIndicatorProps {
  isVisible: boolean;
  /** Direction of the off-screen block relative to the viewport */
  direction?: 'above' | 'below';
  onScrollToBlock: () => void;
  onDismiss: () => void;
}

export const OffScreenAIIndicator = memo<OffScreenAIIndicatorProps>(
  ({ isVisible, direction = 'below', onScrollToBlock, onDismiss }) => {
    const isAbove = direction === 'above';

    return (
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, y: isAbove ? -10 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: isAbove ? -10 : 10 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'absolute left-1/2 -translate-x-1/2 z-20',
              isAbove ? 'top-4' : 'bottom-4'
            )}
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center gap-2 rounded-full bg-warning/10 border border-warning/30 ai-offscreen-indicator px-3 py-1.5 shadow-warm-sm">
              <Sparkles className="h-3.5 w-3.5 text-warning motion-safe:animate-pulse" aria-hidden="true" />
              <button
                type="button"
                onClick={onScrollToBlock}
                className="text-xs font-medium text-warning hover:text-warning/80 focus-visible:ring-2 focus-visible:ring-warning focus-visible:outline-none rounded"
              >
                {isAbove ? 'AI is editing above' : 'AI is editing below'}
              </button>
              <Button
                variant="ghost"
                size="icon"
                onClick={onDismiss}
                className="h-4 w-4 text-warning hover:text-warning/80 focus-visible:ring-2 focus-visible:ring-warning"
              >
                <X className="h-3 w-3" />
                <span className="sr-only">Dismiss</span>
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }
);

OffScreenAIIndicator.displayName = 'OffScreenAIIndicator';
