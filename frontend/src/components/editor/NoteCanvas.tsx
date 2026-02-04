'use client';

/**
 * NoteCanvas - Main editor component for notes
 * Two-column layout: editor (left), AI ChatView panel (right)
 * Per UI Spec v3.3 / Prototype v4: Note-First design with merged header
 * Integrates TipTap with all extensions and virtualization for 1000+ blocks
 *
 * Responsive behavior:
 * - Ultra-large (2xl+): Wider content, larger ChatView panel, more padding
 * - Large desktop (xl-2xl): Standard wide layout
 * - Desktop (lg-xl): Side-by-side layout with ChatView panel
 * - Tablet (md-lg): Collapsible ChatView, full-width editor
 * - Mobile (<md): Overlay ChatView panel, compact header
 */
import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import type { Content, Editor } from '@tiptap/core';
import { observer } from 'mobx-react-lite';
import { reaction } from 'mobx';
import { AlertTriangle, X } from 'lucide-react';
import { toast } from 'sonner';
import type { GhostTextContext } from '@/features/notes/editor/extensions/GhostTextExtension';
import { motion, AnimatePresence } from 'motion/react';
import { getAIStore } from '@/stores/ai/AIStore';
import { useSelectionContext } from '@/features/notes/editor/hooks/useSelectionContext';
import { useContentUpdates } from '@/features/notes/editor/hooks/useContentUpdates';
import { ChatView } from '@/features/ai/ChatView/ChatView';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { createEditorExtensions } from '@/features/notes/editor/extensions';
import { useResponsive } from '@/hooks/useMediaQuery';
import { useWorkspaceStore } from '@/stores/RootStore';
import type { JSONContent } from '@/types';
import { SelectionToolbar } from './SelectionToolbar';
import { InlineNoteHeader } from './InlineNoteHeader';
import { NoteTitleBlock } from './NoteTitleBlock';
import { CollapsedChatStrip } from './CollapsedChatStrip';
import type { User } from '@/types';

export interface NoteCanvasProps {
  /** Note ID for loading */
  noteId: string;
  /** Initial content to load */
  content?: JSONContent;
  /** Read-only mode */
  readOnly?: boolean;
  /** Callback when content changes */
  onChange?: (content: JSONContent) => void;
  /** Callback for manual save (Cmd+S) */
  onSave?: () => void;
  /** Whether the note is currently loading */
  isLoading?: boolean;
  /** Loading/saving error */
  error?: string | null;
  /** Current workspace ID */
  workspaceId?: string;
  /** Note title for inline header */
  title?: string;
  /** Note author */
  author?: User;
  /** Note creation date */
  createdAt?: string;
  /** Note update date */
  updatedAt?: string;
  /** Word count */
  wordCount?: number;
  /** Whether note is pinned */
  isPinned?: boolean;
  /** Whether note has AI-assisted edits */
  isAIAssisted?: boolean;
  /** Topic tags for the note */
  topics?: string[];
  /** Workspace slug for breadcrumb */
  workspaceSlug?: string;
  /** Callback when title changes */
  onTitleChange?: (title: string) => void;
  /** Callback for share action */
  onShare?: () => void;
  /** Callback for export action */
  onExport?: () => void;
  /** Callback for delete action */
  onDelete?: () => void;
  /** Callback for pin toggle */
  onTogglePin?: () => void;
  /** Callback for version history */
  onVersionHistory?: () => void;
}

/**
 * Error boundary fallback for editor crashes
 */
function EditorErrorFallback({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <h3 className="font-semibold text-foreground">Editor Error</h3>
        <p className="mt-1 text-sm text-muted-foreground">{error}</p>
      </div>
      <Button variant="outline" onClick={onRetry}>
        Try Again
      </Button>
    </div>
  );
}

/**
 * Loading skeleton for the editor
 */
function EditorSkeleton() {
  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-4/5" />
      <div className="mt-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="mt-2 h-4 w-11/12" />
        <Skeleton className="mt-2 h-4 w-4/5" />
      </div>
      <div className="mt-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="mt-2 h-4 w-3/4" />
      </div>
    </div>
  );
}

/**
 * NoteCanvas component with three-column layout per Prototype v4
 * Layout: [TOC Tree | Document Canvas | Pilot Suggestions]
 */
export const NoteCanvas = observer(function NoteCanvas({
  noteId,
  content,
  readOnly = false,
  onChange,
  onSave,
  isLoading = false,
  error = null,
  workspaceId,
  title = 'Untitled',
  author,
  createdAt,
  updatedAt,
  wordCount = 0,
  isPinned = false,
  isAIAssisted = false,
  topics,
  workspaceSlug = '',
  onTitleChange,
  onShare,
  onExport,
  onDelete,
  onTogglePin,
  onVersionHistory,
}: NoteCanvasProps) {
  const [editorError, setEditorError] = useState<string | null>(null);
  const [isChatViewOpen, setIsChatViewOpen] = useState(true);

  const editorContainerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Ref to track current editor for ghost text callback
  const editorRef = useRef<Editor | null>(null);
  // Refs for values needed in extension callbacks (avoids useMemo dep changes)
  const noteIdRef = useRef(noteId);
  noteIdRef.current = noteId;
  const titleRef = useRef(title);
  titleRef.current = title;

  const aiStore = getAIStore();
  const workspaceStore = useWorkspaceStore();

  // Demo workspace UUID fallback (matches /chat page pattern)
  const DEMO_WORKSPACE_ID = '00000000-0000-0000-0000-000000000002';

  // Resolve workspace UUID with cascading fallback:
  // 1. workspaceId prop if already UUID
  // 2. Slug lookup from workspace store
  // 3. currentWorkspace from store
  // 4. Demo workspace ID (development fallback)
  const isUUID = workspaceId && /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(workspaceId);
  const resolvedWorkspaceId = isUUID
    ? workspaceId
    : (workspaceId && workspaceStore.getWorkspaceBySlug(workspaceId)?.id) ||
      workspaceStore.currentWorkspace?.id ||
      DEMO_WORKSPACE_ID;

  // Set workspace context on PilotSpaceStore so chat messages include workspaceId
  useEffect(() => {
    aiStore.pilotSpace.setWorkspaceId(resolvedWorkspaceId);
  }, [resolvedWorkspaceId, aiStore.pilotSpace]);

  // Set note context on mount so ChatView can auto-restore conversation history.
  // This triggers ChatView's existing useEffect → resumeSessionForContext(noteId).
  useEffect(() => {
    if (noteId) {
      aiStore.pilotSpace.setNoteContext({
        noteId,
        noteTitle: titleRef.current || 'Untitled',
      });
    }
    return () => {
      aiStore.pilotSpace.setNoteContext(null);
    };
  }, [noteId, aiStore.pilotSpace]);

  // Responsive breakpoints
  const { isSmallScreen, isLargeDesktop } = useResponsive();

  // Ghost text trigger function - delegates to GhostTextStore
  const handleGhostTextTrigger = useCallback(
    (context: GhostTextContext) => {
      if (!noteId) return;
      // Request suggestion from store (handles SSE streaming)
      aiStore.ghostText.requestSuggestion(noteId, context.textBeforeCursor, context.cursorPosition);
    },
    [noteId, aiStore.ghostText]
  );

  // Auto-trigger margin annotations when content changes (debounced in store)
  const handleAnnotationAutoTrigger = useCallback(
    (editor: Editor) => {
      if (!noteId || !editor || editor.isDestroyed) return;

      // Extract blockIds from the editor's document
      const blockIds: string[] = [];
      editor.state.doc.descendants((node) => {
        const blockId = node.attrs?.id || node.attrs?.blockId;
        if (blockId) {
          blockIds.push(blockId);
        }
        return true; // Continue traversal
      });

      if (blockIds.length > 0) {
        aiStore.marginAnnotation.autoTriggerAnnotations(noteId, blockIds, workspaceId);
      }
    },
    [noteId, workspaceId, aiStore.marginAnnotation]
  );

  // State to track when editor is ready for MobX reactions
  const [isEditorReady, setIsEditorReady] = useState(false);

  // Sync ghost text suggestion from store to editor
  useEffect(() => {
    // Use editorRef.current which is set in onCreate callback
    const currentEditor = editorRef.current;
    if (!currentEditor || currentEditor.isDestroyed) return;

    const disposer = reaction(
      () => aiStore.ghostText.suggestion,
      (suggestion: string) => {
        if (!currentEditor.isDestroyed) {
          if (suggestion) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (currentEditor.commands as any).setGhostText?.(suggestion);
          } else {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (currentEditor.commands as any).dismissGhostText?.();
          }
        }
      },
      { fireImmediately: true }
    );

    return () => disposer();
  }, [isEditorReady, aiStore.ghostText]);

  // Sync margin annotations from store to editor extension
  useEffect(() => {
    if (!isEditorReady || !noteId) return;

    const disposer = reaction(
      () => aiStore.marginAnnotation.getAnnotationsForNote(noteId),
      (storeAnnotations) => {
        // Build annotation data map for editor extension
        const annotationMap = new Map();
        storeAnnotations.forEach((annotation) => {
          const existing = annotationMap.get(annotation.blockId) || {
            blockId: annotation.blockId,
            count: 0,
            types: [],
          };
          existing.count += 1;
          if (!existing.types.includes(annotation.type)) {
            existing.types.push(annotation.type);
          }
          annotationMap.set(annotation.blockId, existing);
        });

        // Update editor extension
        const currentEditor = editorRef.current;
        if (currentEditor && !currentEditor.isDestroyed) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (currentEditor.commands as any).setAnnotations?.(annotationMap);
        }
      },
      { fireImmediately: true }
    );

    return () => disposer();
  }, [isEditorReady, noteId, aiStore.marginAnnotation]);

  // Create editor extensions with ghost text and margin annotations
  const extensions = useMemo(
    () =>
      createEditorExtensions({
        placeholder: readOnly ? '' : 'Start typing, or press / for commands...',
        ghostText: {
          enabled: !readOnly,
          onTrigger: handleGhostTextTrigger,
          onAccept: (text: string) => {
            toast.success('AI suggestion accepted', {
              description: `Added: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"`,
            });
          },
        },
        marginAnnotation: {
          annotations: new Map(),
          onClick: (_blockId: string) => {
            // Annotations handled via ChatView now
          },
        },
        slashCommand: {
          onAICommand: async (command: string, cmdEditor: Editor) => {
            // Route all AI slash commands through ChatView
            setIsChatViewOpen(true);

            // Build a message from the command and selected text
            const selectedText = cmdEditor.state.selection.empty
              ? undefined
              : cmdEditor.state.doc.textBetween(
                  cmdEditor.state.selection.from,
                  cmdEditor.state.selection.to
                );

            // Ensure note context is set before sending (useSelectionContext
            // may not have fired yet if the slash command was typed quickly)
            if (noteIdRef.current) {
              aiStore.pilotSpace.setNoteContext({
                noteId: noteIdRef.current,
                noteTitle: titleRef.current || 'Untitled',
                selectedText: selectedText || undefined,
              });
            }

            const commandMessages: Record<string, string> = {
              'extract-issues': `Extract issues from this note${selectedText ? `: "${selectedText}"` : ''}`,
              improve: `Improve this text${selectedText ? `: "${selectedText}"` : ''}`,
              summarize: `Summarize this note${selectedText ? `: "${selectedText}"` : ''}`,
            };

            const message = commandMessages[command] ?? `AI command: ${command}`;

            // Send through ChatView after a tick (let ChatView open first)
            setTimeout(() => {
              aiStore.pilotSpace.sendMessage(message);
            }, 100);
          },
        },
      }),
    [readOnly, handleGhostTextTrigger, aiStore.pilotSpace]
  );

  // Initialize TipTap editor
  const editor = useEditor({
    extensions,
    content: (content ?? {
      type: 'doc',
      content: [{ type: 'paragraph' }],
    }) as Content,
    editable: !readOnly,
    immediatelyRender: false, // Prevent SSR hydration mismatch
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-slate dark:prose-invert max-w-none',
          'prose-p:leading-[1.5] prose-li:leading-[1.5]', // Compact line-height
          'focus:outline-none',
          'min-h-[calc(100vh-200px)]'
        ),
      },
    },
    onUpdate: ({ editor: ed }) => {
      if (onChange) {
        const json = ed.getJSON();
        onChange(json as JSONContent);
      }
      // Auto-trigger margin annotations after content changes (debounced in store)
      handleAnnotationAutoTrigger(ed);
    },
    onCreate: ({ editor: ed }) => {
      setEditorError(null);
      editorRef.current = ed;
      setIsEditorReady(true);
    },
    onDestroy: () => {
      editorRef.current = null;
      setIsEditorReady(false);
    },
  });

  // Update content when prop changes
  useEffect(() => {
    if (editor && content && !editor.isDestroyed) {
      const currentContent = editor.getJSON();
      // Only update if content is different
      if (JSON.stringify(currentContent) !== JSON.stringify(content)) {
        editor.commands.setContent(content as Content);
      }
    }
  }, [editor, content]);

  // Fetch persisted annotations on mount
  useEffect(() => {
    if (noteId && workspaceSlug && editor && !editor.isDestroyed) {
      aiStore.marginAnnotation.fetchAnnotations(workspaceSlug, noteId);
    }
  }, [noteId, workspaceSlug, editor, aiStore.marginAnnotation]);

  // Track selection context for ChatView
  useSelectionContext(editor, aiStore.pilotSpace, noteId, title);

  // Apply AI content updates from PilotSpace
  const { processingBlockIds } = useContentUpdates(
    editor,
    aiStore.pilotSpace,
    noteId,
    resolvedWorkspaceId ?? undefined
  );

  // Update AIBlockProcessingExtension with current processing block IDs
  useEffect(() => {
    if (editor && !editor.isDestroyed) {
      (editor.storage as unknown as Record<string, unknown>).aiBlockProcessing = {
        processingBlockIds,
      };
      // Force decoration update by dispatching an empty transaction
      editor.view.dispatch(editor.state.tr);
    }
  }, [editor, processingBlockIds]);

  // Open ChatView and set note context
  const handleChatViewOpen = useCallback(() => {
    setIsChatViewOpen(true);
    if (noteId) {
      aiStore.pilotSpace.setNoteContext({
        noteId,
        noteTitle: title || 'Untitled',
        selectedText: aiStore.pilotSpace.noteContext?.selectedText,
        selectedBlockIds: aiStore.pilotSpace.noteContext?.selectedBlockIds,
      });
    }
  }, [noteId, title, aiStore.pilotSpace]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd/Ctrl + S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        onSave?.();
      }
      // Cmd/Ctrl + Shift + P to toggle ChatView
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        if (isChatViewOpen) {
          setIsChatViewOpen(false);
        } else {
          handleChatViewOpen();
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isChatViewOpen, handleChatViewOpen, onSave]);

  // Retry on error
  const handleRetry = useCallback(() => {
    setEditorError(null);
    // Trigger reload
    window.location.reload();
  }, []);

  // Show error state
  if (error || editorError) {
    return (
      <EditorErrorFallback error={error ?? editorError ?? 'Unknown error'} onRetry={handleRetry} />
    );
  }

  // Show loading state
  if (isLoading || !editor) {
    return <EditorSkeleton />;
  }

  return (
    <div className="flex h-full bg-background overflow-hidden" data-testid="note-editor">
      {/* Center Panel: Document Canvas - Notion-inspired clean layout */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Inline Note Header - Fixed at top, outside scrollable area */}
        {(title || createdAt) && (
          <InlineNoteHeader
            title={title}
            author={author}
            createdAt={createdAt ?? new Date().toISOString()}
            updatedAt={updatedAt}
            wordCount={wordCount}
            isPinned={isPinned}
            isAIAssisted={isAIAssisted}
            topics={topics}
            workspaceSlug={workspaceSlug}
            onShare={onShare}
            onExport={onExport}
            onDelete={onDelete}
            onTogglePin={onTogglePin}
            onVersionHistory={onVersionHistory}
            disabled={readOnly}
          />
        )}

        {/* Editor Toolbar - AI controls and formatting options */}
        {/* {!readOnly && <EditorToolbar noteId={noteId} workspaceId={workspaceId} />} */}

        {/* Scrollable Editor Area */}
        <div ref={editorContainerRef} className="relative flex-1 overflow-auto bg-background">
          {/* Selection Toolbar */}
          <SelectionToolbar
            editor={editor}
            workspaceId={workspaceId}
            noteId={noteId}
            onChatViewOpen={handleChatViewOpen}
          />

          {/* Editor Content - Responsive padding and width */}
          <div
            ref={scrollRef}
            className={cn(
              'h-full overflow-auto scrollbar-thin',
              // Responsive horizontal padding - more breathing room on larger screens
              'px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20',
              // Responsive vertical padding
              'py-3 sm:py-4 lg:py-6 2xl:py-8'
            )}
          >
            <div
              className={cn(
                'mx-auto document-canvas',
                // Responsive max-width - wider on ultra-large screens for better readability
                'max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px]'
              )}
            >
              {/* Note Title Block - Title as first content block (Notion-style) */}
              <NoteTitleBlock title={title} onTitleChange={onTitleChange} disabled={readOnly} />

              {/* TipTap Editor */}
              <EditorContent editor={editor} />
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel: ChatView Sidebar */}
      <AnimatePresence mode="wait">
        {isChatViewOpen ? (
          <>
            {isSmallScreen ? (
              <>
                {/* Backdrop */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
                  onClick={() => setIsChatViewOpen(false)}
                  aria-hidden="true"
                />
                {/* Slide-over panel */}
                <motion.aside
                  initial={{ x: '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '100%' }}
                  transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                  className={cn(
                    'fixed inset-y-0 right-0 z-50 lg:hidden',
                    'w-full max-w-[400px] sm:max-w-[480px]',
                    'bg-background border-l border-border shadow-xl'
                  )}
                >
                  {/* Close button for mobile */}
                  <div className="absolute top-3 right-3 z-10">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setIsChatViewOpen(false)}
                      className="h-8 w-8 rounded-full"
                    >
                      <X className="h-4 w-4" />
                      <span className="sr-only">Close ChatView</span>
                    </Button>
                  </div>
                  <div className="h-full overflow-hidden">
                    <ChatView
                      store={aiStore.pilotSpace}
                      autoFocus
                      onClose={() => setIsChatViewOpen(false)}
                    />
                  </div>
                </motion.aside>
              </>
            ) : (
              <motion.aside
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: isLargeDesktop ? 480 : 400, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className="hidden lg:flex flex-shrink-0 overflow-hidden border-l border-border"
              >
                <div className={cn('h-full', isLargeDesktop ? 'w-[480px]' : 'w-[400px]')}>
                  <ChatView
                    store={aiStore.pilotSpace}
                    autoFocus
                    onClose={() => setIsChatViewOpen(false)}
                  />
                </div>
              </motion.aside>
            )}
          </>
        ) : null}
      </AnimatePresence>

      {/* Collapsed ChatView strip */}
      {!isChatViewOpen && <CollapsedChatStrip onClick={handleChatViewOpen} />}
    </div>
  );
});

export default NoteCanvas;
