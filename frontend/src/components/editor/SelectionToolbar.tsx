'use client';

/**
 * SelectionToolbar - Floating toolbar on text selection
 * Provides formatting and AI actions
 */
import { useCallback, useEffect, useState, useRef } from 'react';
import type { Editor } from '@tiptap/react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { Bold, Italic, Link2, MessageSquare, Wand2, FileText, TicketPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export interface SelectionToolbarProps {
  /** TipTap editor instance */
  editor: Editor | null;
  /** Workspace ID for AI actions */
  workspaceId?: string;
  /** Note ID for AI actions */
  noteId?: string;
  /** Callback to trigger issue extraction */
  onExtractIssue?: (selectedText: string) => void;
}

interface ToolbarPosition {
  top: number;
  left: number;
}

/**
 * SelectionToolbar floating component
 */
export const SelectionToolbar = observer(function SelectionToolbar({
  editor,
  workspaceId: _workspaceId,
  noteId: _noteId,
  onExtractIssue,
}: SelectionToolbarProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<ToolbarPosition>({ top: 0, left: 0 });
  const toolbarRef = useRef<HTMLDivElement>(null);

  // Calculate toolbar position
  const updatePosition = useCallback(() => {
    if (!editor) return;

    const { from, to, empty } = editor.state.selection;

    // Hide if no selection
    if (empty || from === to) {
      setIsVisible(false);
      return;
    }

    // Get selection coordinates
    const start = editor.view.coordsAtPos(from);
    const end = editor.view.coordsAtPos(to);

    // Calculate center position
    const left = (start.left + end.left) / 2;
    const top = start.top - 50; // Position above selection

    setPosition({ top, left });
    setIsVisible(true);
  }, [editor]);

  // Listen for selection changes
  useEffect(() => {
    if (!editor) return;

    editor.on('selectionUpdate', updatePosition);
    editor.on('blur', () => setIsVisible(false));

    return () => {
      editor.off('selectionUpdate', updatePosition);
      editor.off('blur', () => setIsVisible(false));
    };
  }, [editor, updatePosition]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isVisible) {
        setIsVisible(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isVisible]);

  // Formatting actions
  const toggleBold = useCallback(() => {
    editor?.chain().focus().toggleBold().run();
  }, [editor]);

  const toggleItalic = useCallback(() => {
    editor?.chain().focus().toggleItalic().run();
  }, [editor]);

  const addLink = useCallback(() => {
    const url = window.prompt('Enter URL:');
    if (url) {
      editor?.chain().focus().setLink({ href: url }).run();
    }
  }, [editor]);

  const addComment = useCallback(() => {
    // This would open a comment dialog
    console.log('Add comment');
  }, []);

  // AI actions
  const improveText = useCallback(async () => {
    if (!editor) return;

    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to
    );

    // This would call the AI service
    console.log('Improve text:', selectedText);
  }, [editor]);

  const summarizeText = useCallback(async () => {
    if (!editor) return;

    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to
    );

    // This would call the AI service
    console.log('Summarize:', selectedText);
  }, [editor]);

  const extractIssue = useCallback(async () => {
    if (!editor) return;

    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to
    );

    if (onExtractIssue) {
      onExtractIssue(selectedText);
    }
    setIsVisible(false);
  }, [editor, onExtractIssue]);

  if (!editor) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          ref={toolbarRef}
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.15 }}
          style={{
            position: 'fixed',
            top: position.top,
            left: position.left,
            transform: 'translateX(-50%)',
            zIndex: 50,
          }}
          className={cn(
            'flex items-center gap-0.5 rounded-lg border bg-popover p-1 shadow-lg',
            'animate-in fade-in-0 zoom-in-95'
          )}
          role="toolbar"
          aria-label="Text formatting toolbar"
        >
          {/* Formatting actions */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={editor.isActive('bold') ? 'secondary' : 'ghost'}
                size="icon-sm"
                onClick={toggleBold}
                aria-label="Bold"
              >
                <Bold className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Bold (Cmd+B)</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={editor.isActive('italic') ? 'secondary' : 'ghost'}
                size="icon-sm"
                onClick={toggleItalic}
                aria-label="Italic"
              >
                <Italic className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Italic (Cmd+I)</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={editor.isActive('link') ? 'secondary' : 'ghost'}
                size="icon-sm"
                onClick={addLink}
                aria-label="Add link"
              >
                <Link2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add link (Cmd+K)</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" onClick={addComment} aria-label="Add comment">
                <MessageSquare className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add comment</TooltipContent>
          </Tooltip>

          <Separator orientation="vertical" className="mx-1 h-6" />

          {/* AI actions */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                onClick={improveText}
                aria-label="Improve with AI"
              >
                <Wand2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Improve with AI</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                onClick={summarizeText}
                aria-label="Summarize"
              >
                <FileText className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Summarize</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                onClick={extractIssue}
                aria-label="Extract issue"
              >
                <TicketPlus className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Extract as issue</TooltipContent>
          </Tooltip>
        </motion.div>
      )}
    </AnimatePresence>
  );
});

export default SelectionToolbar;
