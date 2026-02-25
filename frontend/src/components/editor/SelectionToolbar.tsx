'use client';

/**
 * SelectionToolbar - Floating toolbar on text selection
 * Provides formatting and AI actions
 *
 * Integrated with PilotSpace AI for selection-based actions:
 * - Ask Pilot: Opens ChatView with selection context
 * - Enhance: Improves selected text with AI
 * - Extract Issues: Extracts actionable items from selection
 */
import { useCallback, useEffect, useState, useRef } from 'react';
import type { Editor } from '@tiptap/react';
import { motion, AnimatePresence } from 'motion/react';
import { Bold, Italic, Link2, MessageSquare, Wand2, TicketPlus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useSelectionAIActions } from '@/features/notes/editor/hooks/useSelectionAIActions';
import { getAIStore } from '@/stores/ai/AIStore';

export interface SelectionToolbarProps {
  /** TipTap editor instance */
  editor: Editor | null;
  /** Workspace ID for AI actions */
  workspaceId?: string;
  /** Note ID for AI actions */
  noteId?: string;
  /** Callback to open ChatView */
  onChatViewOpen?: () => void;
}

interface ToolbarPosition {
  top: number;
  left: number;
}

/**
 * SelectionToolbar floating component
 *
 * NOTE: Intentionally NOT wrapped in observer(). This component is rendered inside
 * NoteCanvasLayout which is adjacent to TipTap's ReactNodeViewRenderer. MobX observer()
 * uses useSyncExternalStore which calls flushSync when observables change — this conflicts
 * with TipTap's NodeView creation during React's rendering lifecycle (nested flushSync error).
 * aiStore.pilotSpace is a stable singleton so observer() tracking provides no benefit.
 */
export function SelectionToolbar({
  editor,
  workspaceId: _workspaceId,
  noteId,
  onChatViewOpen,
}: SelectionToolbarProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<ToolbarPosition>({ top: 0, left: 0 });
  const toolbarRef = useRef<HTMLDivElement>(null);

  // Get AI store and selection actions
  const aiStore = getAIStore();
  const { askPilot, enhanceSelection, extractIssues } = useSelectionAIActions(
    editor,
    aiStore.pilotSpace,
    noteId || '',
    onChatViewOpen
  );

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

  // AI actions - Wire to new hooks
  const handleAskPilot = useCallback(async () => {
    await askPilot();
    setIsVisible(false);
  }, [askPilot]);

  const handleEnhance = useCallback(async () => {
    await enhanceSelection();
    setIsVisible(false);
  }, [enhanceSelection]);

  const handleExtractIssues = useCallback(async () => {
    // Use new AI-based extraction
    await extractIssues();
    setIsVisible(false);
  }, [extractIssues]);

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
          data-testid="selection-toolbar"
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

          {/* AI actions - Integrated with PilotSpace */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                data-testid="ask-pilot-button"
                onClick={handleAskPilot}
                aria-label="Ask Pilot"
              >
                <MessageSquare className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Ask Pilot about selection</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                data-testid="enhance-button"
                onClick={handleEnhance}
                aria-label="Enhance with AI"
              >
                <Wand2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Enhance with AI</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ai-subtle"
                size="icon-sm"
                data-testid="extract-issues-button"
                onClick={handleExtractIssues}
                aria-label="Extract issues"
              >
                <TicketPlus className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Extract actionable issues</TooltipContent>
          </Tooltip>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SelectionToolbar;
