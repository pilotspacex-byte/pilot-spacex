'use client';

/**
 * NoteCanvasMobileLayout - Mobile/tablet slide-over ChatView layout.
 *
 * Extracted from NoteCanvas to reduce file size.
 * Renders full-width editor with AnimatePresence slide-over ChatView panel
 * for screens below the `lg` breakpoint.
 *
 * @module components/editor/NoteCanvasMobileLayout
 */
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { CollapsedChatStrip } from './CollapsedChatStrip';

export interface NoteCanvasMobileLayoutProps {
  /** The editor content JSX to render full-width */
  editorContent: React.ReactNode;
  /** The ChatView JSX to render in the slide-over */
  chatViewContent: React.ReactNode;
  /** Whether the ChatView panel is open */
  isChatViewOpen: boolean;
  /** Close the ChatView panel */
  onClose: () => void;
  /** Open the ChatView panel */
  onOpen: () => void;
}

/**
 * Mobile/Tablet layout: full-width editor with slide-over ChatView.
 */
export function NoteCanvasMobileLayout({
  editorContent,
  chatViewContent,
  isChatViewOpen,
  onClose,
  onOpen,
}: NoteCanvasMobileLayoutProps) {
  return (
    <>
      {/* Full-width editor */}
      <div className="flex-1 min-w-0">{editorContent}</div>

      {/* Mobile ChatView slide-over */}
      <AnimatePresence mode="wait">
        {isChatViewOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
              onClick={onClose}
              aria-hidden="true"
            />
            {/* Slide-over panel */}
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className={cn(
                'fixed inset-y-0 right-0 z-50',
                'w-full max-w-[400px] sm:max-w-[480px]',
                'bg-background border-l border-border shadow-xl'
              )}
            >
              {/* Close button for mobile */}
              <div className="absolute top-3 right-3 z-10">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="h-8 w-8 rounded-full"
                >
                  <X className="h-4 w-4" />
                  <span className="sr-only">Close ChatView</span>
                </Button>
              </div>
              <div className="h-full overflow-hidden">{chatViewContent}</div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Collapsed ChatView strip for mobile */}
      {!isChatViewOpen && <CollapsedChatStrip onClick={onOpen} />}
    </>
  );
}
