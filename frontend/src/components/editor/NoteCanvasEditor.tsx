'use client';

/**
 * NoteCanvasEditor - Editor initialization, TipTap hooks, and all editor logic.
 * Extracted from NoteCanvas to stay under 700-line limit.
 *
 * Exports:
 * - useNoteCanvasEditor: Custom hook encapsulating TipTap editor setup,
 *   ghost text, annotations, keyboard shortcuts, AI integration.
 * - extractFirstHeadingText: Utility for syncing note title from headings.
 * - EditorErrorFallback / EditorSkeleton: UI states for loading/error.
 * - NoteCanvasProps: Props interface for the NoteCanvas component.
 */
import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useEditor } from '@tiptap/react';
import type { Content, Editor } from '@tiptap/core';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import type { GhostTextContext } from '@/features/notes/editor/extensions/GhostTextExtension';
import { usePanelRef } from 'react-resizable-panels';
import { getAIStore } from '@/stores/ai/AIStore';
import { useSelectionContext } from '@/features/notes/editor/hooks/useSelectionContext';
import { useContentUpdates } from '@/features/notes/editor/hooks/useContentUpdates';
import { cn } from '@/lib/utils';
import { createEditorExtensions } from '@/features/notes/editor/extensions';
import '@/features/notes/editor/extensions/note-link.css';
import { notesApi } from '@/services/api/notes';
import { useResponsive } from '@/hooks/useMediaQuery';
import type { JSONContent, User, LinkedIssueBrief } from '@/types';
import { useAIAutoScroll } from '@/hooks/useAIAutoScroll';
import { useEditorSync } from './hooks/useEditorSync';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

/** Update AIBlockProcessingExtension storage — extracted to avoid lint mutation error. */
function updateAIBlockProcessingStorage(editor: Editor, processingBlockIds: string[]) {
  (editor.storage as unknown as Record<string, unknown>).aiBlockProcessing = {
    processingBlockIds,
  };
  queueMicrotask(() => {
    if (!editor.isDestroyed) {
      editor.view.dispatch(editor.state.tr);
    }
  });
}

/**
 * Extract the text content of the first heading node found in the editor document.
 * Used to sync the note title from the first H1/H2/H3 in the document.
 * Returns empty string if no heading is found.
 */
export function extractFirstHeadingText(doc: {
  forEach: (callback: (node: { type: { name: string }; textContent: string }) => void) => void;
}): string {
  let firstHeadingText = '';
  doc.forEach((node) => {
    if (!firstHeadingText && node.type.name === 'heading') {
      firstHeadingText = node.textContent;
    }
  });
  return firstHeadingText;
}

export interface NoteCanvasProps {
  noteId: string;
  content?: JSONContent;
  readOnly?: boolean;
  onChange?: (content: JSONContent) => void;
  onSave?: () => void;
  isLoading?: boolean;
  error?: string | null;
  workspaceId?: string;
  title?: string;
  author?: User;
  createdAt?: string;
  updatedAt?: string;
  wordCount?: number;
  isPinned?: boolean;
  isAIAssisted?: boolean;
  topics?: string[];
  workspaceSlug?: string;
  onTitleChange?: (title: string) => void;
  onShare?: () => void;
  onExport?: () => void;
  onDelete?: () => void;
  onTogglePin?: () => void;
  onVersionHistory?: () => void;
  projectId?: string;
  linkedIssues?: LinkedIssueBrief[];
  /** Callback to trigger issue extraction from note content */
  onExtractIssues?: (params: {
    noteId: string;
    noteTitle: string;
    noteContent: Record<string, unknown>;
    selectedText?: string;
  }) => void;
}

/**
 * Error boundary fallback for editor crashes
 */
export function EditorErrorFallback({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <h3 className="font-semibold text-foreground">Editor Error</h3>
        <p className="mt-1 text-xs text-muted-foreground">{error}</p>
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
export function EditorSkeleton() {
  return (
    <div className="flex h-full flex-col gap-3 p-4">
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

/** Return type of useNoteCanvasEditor */
export interface NoteCanvasEditorState {
  editor: Editor | null;
  editorContainerRef: React.RefObject<HTMLDivElement | null>;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  chatPanelRef: ReturnType<typeof usePanelRef>;
  isChatViewOpen: boolean;
  setIsChatViewOpen: (open: boolean) => void;
  chatPanelState: 'min' | 'max' | 'mid';
  isSmallScreen: boolean;
  aiStore: ReturnType<typeof getAIStore>;
  processingBlockIds: string[];
  hasOffScreenUpdate: boolean;
  offScreenDirection: 'above' | 'below';
  scrollToBlock: () => void;
  dismissIndicator: () => void;
  handleChatViewOpen: () => void;
  handleChatPanelToggle: () => void;
  handleChatPanelResize: (size: { asPercentage: number; inPixels: number }) => void;
  handleRetry: () => void;
  editorError: string | null;
}

/**
 * Custom hook encapsulating all TipTap editor initialization, hooks, and logic.
 * Returns state and handlers needed by the layout component.
 */
export function useNoteCanvasEditor(props: NoteCanvasProps): NoteCanvasEditorState {
  const router = useRouter();
  const {
    noteId,
    content,
    readOnly = false,
    onChange,
    onSave,
    workspaceId,
    title = 'Untitled',
    workspaceSlug = '',
    onTitleChange,
    onExtractIssues,
  } = props;

  const [editorError, setEditorError] = useState<string | null>(null);
  const [isChatViewOpen, setIsChatViewOpen] = useState(true);
  const [chatPanelState, setChatPanelState] = useState<'min' | 'max' | 'mid'>('min');

  const editorContainerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const chatPanelRef = usePanelRef();

  const editorRef = useRef<Editor | null>(null);
  const noteIdRef = useRef(noteId);
  const titleRef = useRef(title);
  const onTitleChangeRef = useRef(onTitleChange);

  const onExtractIssuesRef = useRef(onExtractIssues);

  // Sync refs in effect to avoid ref updates during render
  useEffect(() => {
    noteIdRef.current = noteId;
    titleRef.current = title;
    onTitleChangeRef.current = onTitleChange;
    onExtractIssuesRef.current = onExtractIssues;
  }, [noteId, title, onTitleChange, onExtractIssues]);

  const aiStore = getAIStore();

  // workspaceId from the parent (NoteDetailPage) may be a slug as the last fallback when
  // WorkspaceGuard hasn't resolved yet (workspace?.id ?? workspaceStore.currentWorkspace?.id ?? workspaceSlug).
  // Only propagate to API calls if it looks like a UUID — prevents sending slugs to backend endpoints
  // that expect UUIDs (ghost text SSE, issue creation, margin annotation headers, AI session context).
  // @see NoteDetailPage — expected sole consumer; must pre-resolve workspaceId before passing as prop.
  const isWorkspaceUUID = workspaceId ? /^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(workspaceId) : false;
  const resolvedWorkspaceId = isWorkspaceUUID ? workspaceId : undefined;

  // Set workspace context on PilotSpaceStore
  useEffect(() => {
    aiStore.pilotSpace.setWorkspaceId(resolvedWorkspaceId ?? null);
  }, [resolvedWorkspaceId, aiStore.pilotSpace]);

  // Set note context on mount
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

  const { isSmallScreen } = useResponsive();

  // Ghost text trigger
  const handleGhostTextTrigger = useCallback(
    (context: GhostTextContext) => {
      if (!noteId || !resolvedWorkspaceId) return;
      const lastNewline = context.textBeforeCursor.lastIndexOf('\n');
      const prefix =
        lastNewline >= 0
          ? context.textBeforeCursor.slice(lastNewline + 1)
          : context.textBeforeCursor;
      aiStore.ghostText.requestSuggestion(
        noteId,
        context.textBeforeCursor,
        prefix,
        resolvedWorkspaceId,
        context.blockType,
        titleRef.current || undefined
      );
    },
    [noteId, resolvedWorkspaceId, aiStore.ghostText]
  );

  // Auto-trigger margin annotations
  const handleAnnotationAutoTrigger = useCallback(
    (editor: Editor) => {
      if (!noteId || !editor || editor.isDestroyed) return;

      const blockIds: string[] = [];
      editor.state.doc.descendants((node) => {
        const blockId = node.attrs?.id || node.attrs?.blockId;
        if (blockId) {
          blockIds.push(blockId);
        }
        return true;
      });

      if (blockIds.length > 0) {
        aiStore.marginAnnotation.autoTriggerAnnotations(noteId, blockIds, resolvedWorkspaceId);
      }
    },
    [noteId, resolvedWorkspaceId, aiStore.marginAnnotation]
  );

  const [isEditorReady, setIsEditorReady] = useState(false);

  // Sync note title from first heading
  const syncTitleFromFirstHeading = useCallback((ed: Editor) => {
    const headingText = extractFirstHeadingText(ed.state.doc);
    if (headingText && headingText !== titleRef.current && onTitleChangeRef.current) {
      onTitleChangeRef.current(headingText);
    }
  }, []);

  // Create editor extensions — refs are only accessed inside event callbacks, not during render
  const extensions = useMemo(
    () =>
      // eslint-disable-next-line react-hooks/refs
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
        marginAnnotationAutoTrigger: {
          noteId,
        },
        enableNoteLinks: !readOnly && !!resolvedWorkspaceId,
        noteLink: {
          workspaceSlug,
          currentNoteId: noteId,
          onSearch: async (query: string) => {
            if (!resolvedWorkspaceId) return [];
            return notesApi.searchNotes(resolvedWorkspaceId, query);
          },
          onLinkCreated: (targetNoteId: string, blockId?: string) => {
            if (!resolvedWorkspaceId) return;
            notesApi
              .linkNote(resolvedWorkspaceId, noteId, targetNoteId, 'inline', blockId)
              .catch(() => {
                toast.error('Failed to save note link');
              });
          },
          onClick: (targetNoteId: string) => {
            if (workspaceSlug) router.push(`/${workspaceSlug}/notes/${targetNoteId}`);
          },
        },
        slashCommand: {
          onAICommand: async (command: string, cmdEditor: Editor) => {
            const selectedText = cmdEditor.state.selection.empty
              ? undefined
              : cmdEditor.state.doc.textBetween(
                  cmdEditor.state.selection.from,
                  cmdEditor.state.selection.to
                );

            // Route extract-issues to the dedicated extraction pipeline
            if (command === 'extract-issues' && onExtractIssuesRef.current && noteIdRef.current) {
              onExtractIssuesRef.current({
                noteId: noteIdRef.current,
                noteTitle: titleRef.current || 'Untitled',
                noteContent: cmdEditor.getJSON() as Record<string, unknown>,
                selectedText: selectedText || undefined,
              });
              return;
            }

            setIsChatViewOpen(true);

            if (noteIdRef.current) {
              const selectedBlockIds: string[] = [];
              if (cmdEditor && !cmdEditor.state.selection.empty) {
                const { from, to } = cmdEditor.state.selection;
                cmdEditor.state.doc.nodesBetween(from, to, (node) => {
                  const blockId = node.attrs?.id || node.attrs?.blockId;
                  if (blockId && !selectedBlockIds.includes(blockId)) {
                    selectedBlockIds.push(blockId);
                  }
                  return true;
                });
              }

              aiStore.pilotSpace.setNoteContext({
                noteId: noteIdRef.current,
                noteTitle: titleRef.current || 'Untitled',
                selectedText: selectedText || undefined,
                selectedBlockIds: selectedBlockIds.length > 0 ? selectedBlockIds : undefined,
              });
            }

            const commandMessages: Record<string, string> = {
              improve: `Improve this text${selectedText ? `: "${selectedText}"` : ''}`,
              summarize: `Summarize this note${selectedText ? `: "${selectedText}"` : ''}`,
            };

            const message = commandMessages[command] ?? `AI command: ${command}`;

            setTimeout(() => {
              aiStore.pilotSpace.sendMessage(message);
            }, 100);
          },
        },
      }),
    [
      readOnly,
      handleGhostTextTrigger,
      aiStore.pilotSpace,
      resolvedWorkspaceId,
      noteId,
      workspaceSlug,
      router,
    ]
  );

  // Initialize TipTap editor
  const editor = useEditor({
    extensions,
    content: (content ?? {
      type: 'doc',
      content: [{ type: 'paragraph' }],
    }) as Content,
    editable: !readOnly,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-slate dark:prose-invert max-w-none',
          'prose-p:leading-[1.5] prose-li:leading-[1.5]',
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
      syncTitleFromFirstHeading(ed);
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
      if (JSON.stringify(currentContent) !== JSON.stringify(content)) {
        editor.commands.setContent(content as Content);
      }
    }
  }, [editor, content]);

  // Sync ghost text + margin annotations from MobX stores
  useEditorSync(editorRef, isEditorReady, aiStore, noteId, workspaceSlug, editor);

  // Track selection context for ChatView
  useSelectionContext(editor, aiStore.pilotSpace, noteId, title);

  // Apply AI content updates
  const { processingBlockIds, userEditingBlockId } = useContentUpdates(
    editor,
    aiStore.pilotSpace,
    noteId,
    resolvedWorkspaceId
  );

  // Auto-scroll to AI-focused blocks
  const { hasOffScreenUpdate, offScreenDirection, scrollToBlock, dismissIndicator } =
    useAIAutoScroll(scrollRef, processingBlockIds, userEditingBlockId);

  // Populate noteTitles storage from existing links on mount (C-3 fix)
  useEffect(() => {
    if (!resolvedWorkspaceId || !noteId || !editor || editor.isDestroyed) return;
    let cancelled = false;
    notesApi
      .getNoteLinks(resolvedWorkspaceId, noteId)
      .then((links) => {
        if (cancelled || !editor || editor.isDestroyed) return;
        const storage = (editor.storage as unknown as Record<string, unknown>).noteLink as
          | { noteTitles?: Map<string, string> }
          | undefined;
        if (!storage?.noteTitles) return;
        for (const link of links) {
          if (link.targetNoteTitle) {
            storage.noteTitles.set(link.targetNoteId, link.targetNoteTitle);
          }
        }
        // Trigger re-render of NoteLinkComponents via a no-op transaction
        if (!editor.isDestroyed) {
          editor.view.dispatch(editor.state.tr);
        }
      })
      .catch(() => {
        /* silently ignore — titles will show "Loading..." */
      });
    return () => {
      cancelled = true;
    };
  }, [editor, resolvedWorkspaceId, noteId]);

  // Update AIBlockProcessingExtension with current processing block IDs
  useEffect(() => {
    if (editor && !editor.isDestroyed) {
      updateAIBlockProcessingStorage(editor, processingBlockIds);
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
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        onSave?.();
      }
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

  // Toggle ChatView panel size
  const handleChatPanelToggle = useCallback(() => {
    const panel = chatPanelRef.current;
    if (!panel) return;

    if (chatPanelState === 'min' || chatPanelState === 'mid') {
      panel.resize('50%');
      setChatPanelState('max');
    } else {
      panel.resize('30%');
      setChatPanelState('min');
    }
  }, [chatPanelState, chatPanelRef]);

  // Update panel state when resized manually
  const handleChatPanelResize = useCallback((size: { asPercentage: number; inPixels: number }) => {
    const pct = size.asPercentage;
    if (pct <= 39) {
      setChatPanelState('min');
    } else if (pct >= 49) {
      setChatPanelState('max');
    } else {
      setChatPanelState('mid');
    }
  }, []);

  // Retry on error
  const handleRetry = useCallback(() => {
    setEditorError(null);
    window.location.reload();
  }, []);

  return {
    editor,
    editorContainerRef,
    scrollRef,
    chatPanelRef,
    isChatViewOpen,
    setIsChatViewOpen,
    chatPanelState,
    isSmallScreen,
    aiStore,
    processingBlockIds,
    hasOffScreenUpdate,
    offScreenDirection,
    scrollToBlock,
    dismissIndicator,
    handleChatViewOpen,
    handleChatPanelToggle,
    handleChatPanelResize,
    handleRetry,
    editorError,
  };
}
