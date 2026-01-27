'use client';

/**
 * NoteCanvas - Main editor component for notes
 * Two-column layout: editor (left), pilot suggestions with TOC (right)
 * Per UI Spec v3.3 / Prototype v4: Note-First design with merged header
 * Integrates TipTap with all extensions and virtualization for 1000+ blocks
 *
 * Responsive behavior:
 * - Ultra-large (2xl+): Wider content, larger suggestions panel, more padding
 * - Large desktop (xl-2xl): Standard wide layout
 * - Desktop (lg-xl): Side-by-side layout with suggestions panel
 * - Tablet (md-lg): Collapsible suggestions, full-width editor
 * - Mobile (<md): Overlay suggestions panel, compact header
 */
import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import type { Content, Editor } from '@tiptap/core';
import { observer } from 'mobx-react-lite';
import { reaction } from 'mobx';
import { AlertTriangle, X, Sparkles, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { IssueExtractionPanel, type ExtractedIssue } from './IssueExtractionPanel';
import type { GhostTextContext } from '@/features/notes/editor/extensions/GhostTextExtension';
import { motion, AnimatePresence } from 'motion/react';
import { getAIStore } from '@/stores/ai/AIStore';
import { useSelectionContext } from '@/features/notes/editor/hooks/useSelectionContext';
import { ChatView } from '@/features/ai/ChatView/ChatView';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { createEditorExtensions } from '@/features/notes/editor/extensions';
import { useResponsive } from '@/hooks/useMediaQuery';
import type { JSONContent, NoteAnnotation } from '@/types';
import { MarginAnnotations } from './MarginAnnotations';
import { SelectionToolbar } from './SelectionToolbar';
import { AskPilotInput } from './AskPilotInput';
import { InlineNoteHeader } from './InlineNoteHeader';
import { NoteTitleBlock } from './NoteTitleBlock';
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
  /** Workspace slug for breadcrumb */
  workspaceSlug?: string;
  /** Whether right suggestions panel is collapsed by default */
  suggestionsCollapsed?: boolean;
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
  workspaceSlug = '',
  suggestionsCollapsed: initialSuggestionsCollapsed = false,
  onTitleChange,
  onShare,
  onExport,
  onDelete,
  onTogglePin,
  onVersionHistory,
}: NoteCanvasProps) {
  const [editorError, setEditorError] = useState<string | null>(null);
  const [isSuggestionsCollapsed, setIsSuggestionsCollapsed] = useState(initialSuggestionsCollapsed);
  const [extractedIssues, setExtractedIssues] = useState<ExtractedIssue[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [showExtractionPanel, setShowExtractionPanel] = useState(false);
  const [extractionInsertPos, setExtractionInsertPos] = useState<number | null>(null);
  const [isChatViewOpen, setIsChatViewOpen] = useState(false);

  const editorContainerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Ref to track current editor for ghost text callback
  const editorRef = useRef<Editor | null>(null);
  const aiStore = getAIStore();

  // Get annotations from store instead of props
  const annotations = aiStore.marginAnnotation.getAnnotationsForNote(noteId);

  // Responsive breakpoints
  const { isSmallScreen, isLargeDesktop } = useResponsive();

  // Auto-collapse suggestions on smaller screens (only when transitioning to small screen)
  useEffect(() => {
    if (isSmallScreen) {
      setIsSuggestionsCollapsed(true);
    }
  }, [isSmallScreen]);

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

  // Issue extraction handler - calls backend API with SSE streaming
  const handleExtractIssues = useCallback(
    async (selectedText?: string) => {
      const currentEditor = editorRef.current;
      if (!currentEditor || currentEditor.isDestroyed) return;

      setIsExtracting(true);
      setShowExtractionPanel(true);
      setExtractedIssues([]); // Clear previous issues

      // Capture insertion position (end of current selection or cursor position)
      // Find the end of the current paragraph/block for insertion
      const { $to } = currentEditor.state.selection;
      const endOfBlock = $to.end($to.depth);
      setExtractionInsertPos(endOfBlock);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
        const noteContent = currentEditor.getJSON();

        const response = await fetch(`${apiUrl}/notes/${noteId}/extract-issues`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(workspaceId ? { 'X-Workspace-ID': workspaceId } : {}),
          },
          credentials: 'include',
          body: JSON.stringify({
            note_id: noteId,
            note_title: title,
            note_content: noteContent,
            selected_text: selectedText,
            available_labels: [],
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to extract issues (${response.status}): ${errorText}`);
        }

        // Parse SSE stream
        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        const extractedIssues: ExtractedIssue[] = [];
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          let currentEventType = '';
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim();
            } else if (line.startsWith('data:') && currentEventType === 'issue') {
              try {
                const issueData = JSON.parse(line.slice(5).trim());
                const issue: ExtractedIssue = {
                  id: crypto.randomUUID(),
                  title: issueData.title,
                  description: issueData.description,
                  suggestedLabels: issueData.labels || [],
                  priority: (issueData.priority === 1
                    ? 'high'
                    : issueData.priority === 2
                      ? 'medium'
                      : 'low') as ExtractedIssue['priority'],
                  confidence: issueData.confidence_score || 0,
                  confidenceTag: issueData.confidence_tag as ExtractedIssue['confidenceTag'],
                  sourceBlockId: issueData.source_block_ids?.[0] || '',
                  sourceText: issueData.rationale || '',
                };
                extractedIssues.push(issue);
                setExtractedIssues([...extractedIssues]); // Update state incrementally
              } catch {
                // Skip invalid JSON
              }
            } else if (line.startsWith('data:') && currentEventType === 'error') {
              try {
                const errorData = JSON.parse(line.slice(5).trim());
                throw new Error(errorData.message || 'Extraction failed');
              } catch {
                // Skip invalid JSON
              }
            }
          }
        }

        if (extractedIssues.length > 0) {
          toast.success(
            `Found ${extractedIssues.length} potential issue${extractedIssues.length > 1 ? 's' : ''}`
          );
        } else {
          toast.info('No issues found in the selected content');
        }
      } catch (err) {
        console.error('Issue extraction error:', err);
        toast.error(err instanceof Error ? err.message : 'Failed to extract issues');
      } finally {
        setIsExtracting(false);
      }
    },
    [workspaceId, title, noteId]
  );

  // AI command handler for slash commands
  const handleAICommand = useCallback(
    async (command: string, editor: Editor) => {
      if (command === 'extract-issues') {
        const selectedText = editor.state.selection.empty
          ? undefined
          : editor.state.doc.textBetween(editor.state.selection.from, editor.state.selection.to);
        await handleExtractIssues(selectedText);
      } else if (command === 'improve') {
        toast.info('AI text improvement coming soon');
      } else if (command === 'summarize') {
        toast.info('AI summarization coming soon');
      }
    },
    [handleExtractIssues]
  );

  // Handle annotation click to scroll to block
  const handleAnnotationClick = useCallback((annotation: NoteAnnotation) => {
    // Scroll to the block in the editor
    if (editorContainerRef.current) {
      const blockElement = editorContainerRef.current.querySelector(
        `[data-blockId="${annotation.blockId}"]`
      );
      if (blockElement) {
        blockElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, []);

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
          onClick: (blockId: string) => {
            // Scroll to annotation in margin panel
            const annotation = aiStore.marginAnnotation
              .getAnnotationsForNote(noteId)
              .find((a) => a.blockId === blockId);
            if (annotation) {
              handleAnnotationClick(annotation);
            }
          },
        },
        slashCommand: {
          onAICommand: handleAICommand,
        },
      }),
    [
      readOnly,
      handleGhostTextTrigger,
      handleAICommand,
      noteId,
      aiStore.marginAnnotation,
      handleAnnotationClick,
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
    immediatelyRender: false, // Prevent SSR hydration mismatch
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-slate dark:prose-invert max-w-none',
          'prose-p:leading-[1.75] prose-li:leading-[1.75]', // UI Spec v3.3: line-height 1.75
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
  useSelectionContext(editor, aiStore.pilotSpace, noteId);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd/Ctrl + S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        onSave?.();
      }
      // Cmd/Ctrl + Shift + P to toggle ChatView
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'p') {
        e.preventDefault();
        setIsChatViewOpen((prev) => !prev);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editor, aiStore.pilotSpace, noteId, onSave]);

  // Handle annotation actions
  const handleAnnotationAccept = useCallback(
    async (annotation: NoteAnnotation) => {
      if (!editor || !workspaceSlug || annotation.type !== 'suggestion') return;

      try {
        // Find the block position in the editor by blockId
        let blockPos: number | null = null;
        let blockEndPos: number | null = null;

        editor.state.doc.descendants((node, pos) => {
          if (node.attrs?.id === annotation.blockId || node.attrs?.blockId === annotation.blockId) {
            blockPos = pos;
            blockEndPos = pos + node.nodeSize;
            return false; // Stop iteration
          }
          return true;
        });

        // Insert the suggestion content after the block
        if (blockPos !== null && blockEndPos !== null) {
          // Create a new paragraph with the suggestion content
          editor
            .chain()
            .focus()
            .insertContentAt(blockEndPos, {
              type: 'paragraph',
              content: [{ type: 'text', text: annotation.content }],
            })
            .run();
        } else {
          // Fallback: Insert at the end of the document if block not found
          editor
            .chain()
            .focus()
            .insertContentAt(editor.state.doc.content.size, {
              type: 'paragraph',
              content: [{ type: 'text', text: annotation.content }],
            })
            .run();
        }

        // Update status in backend
        await aiStore.marginAnnotation.updateAnnotationStatus(
          workspaceSlug,
          noteId,
          annotation.id,
          'accepted'
        );

        toast.success('Suggestion applied', {
          description: `Added: "${annotation.content.substring(0, 50)}${annotation.content.length > 50 ? '...' : ''}"`,
        });
      } catch (_err) {
        toast.error('Failed to apply suggestion');
      }
    },
    [editor, workspaceSlug, noteId, aiStore.marginAnnotation]
  );

  const handleAnnotationReject = useCallback(
    async (annotation: NoteAnnotation) => {
      if (!workspaceSlug) return;
      try {
        await aiStore.marginAnnotation.updateAnnotationStatus(
          workspaceSlug,
          noteId,
          annotation.id,
          'rejected'
        );
        toast.info('Suggestion dismissed');
      } catch (_err) {
        toast.error('Failed to dismiss suggestion');
      }
    },
    [workspaceSlug, noteId, aiStore.marginAnnotation]
  );

  const handleAnnotationDismiss = useCallback(
    async (annotation: NoteAnnotation) => {
      if (!workspaceSlug) return;
      try {
        await aiStore.marginAnnotation.updateAnnotationStatus(
          workspaceSlug,
          noteId,
          annotation.id,
          'dismissed'
        );
      } catch (err) {
        console.error('Failed to dismiss annotation:', err);
      }
    },
    [workspaceSlug, noteId, aiStore.marginAnnotation]
  );

  // Issue extraction panel handlers - create issues in backend and insert into note
  const handleCreateIssue = useCallback(
    async (issue: ExtractedIssue) => {
      const currentEditor = editorRef.current;
      if (!currentEditor || currentEditor.isDestroyed) return;
      if (!workspaceId) {
        toast.error('Workspace not found');
        return;
      }

      try {
        // Map priority string to IssuePriority type
        const priorityMap: Record<string, 'urgent' | 'high' | 'medium' | 'low' | 'none'> = {
          high: 'high',
          medium: 'medium',
          low: 'low',
        };

        // Create the issue in the backend (backend auto-selects project if not provided)
        const { issuesApi } = await import('@/services/api/issues');
        const createdIssue = await issuesApi.create(workspaceId, {
          title: issue.title,
          description: issue.description,
          priority: priorityMap[issue.priority] || 'medium',
          type: 'task',
          state: 'backlog',
          labels: issue.suggestedLabels,
          sourceNoteId: noteId,
        });

        // Insert at stored position or current cursor
        const insertPos = extractionInsertPos ?? currentEditor.state.selection.to;

        // Insert inline issue node with real issue data
        currentEditor
          .chain()
          .focus()
          .insertContentAt(insertPos, [
            {
              type: 'inlineIssue',
              attrs: {
                issueId: createdIssue.id,
                issueKey: createdIssue.identifier,
                title: createdIssue.title,
                type: createdIssue.type || 'task',
                state: createdIssue.state,
                priority: createdIssue.priority,
                sourceBlockId: issue.sourceBlockId || null,
                isNew: true,
              },
            },
            { type: 'text', text: ' ' }, // Add space after issue
          ])
          .run();

        // Update insertion position for next issue
        setExtractionInsertPos((prev) => (prev ?? insertPos) + 2);

        toast.success(`Issue created: ${createdIssue.identifier}`);
        setExtractedIssues((prev) => prev.filter((i) => i.id !== issue.id));
      } catch (err) {
        console.error('Failed to create issue:', err);
        toast.error('Failed to create issue');
      }
    },
    [extractionInsertPos, workspaceId, noteId]
  );

  const handleCreateAllIssues = useCallback(async () => {
    const currentEditor = editorRef.current;
    if (!currentEditor || currentEditor.isDestroyed || extractedIssues.length === 0) return;
    if (!workspaceId) {
      toast.error('Workspace not found');
      return;
    }

    try {
      // Map priority string to IssuePriority type
      const priorityMap: Record<string, 'urgent' | 'high' | 'medium' | 'low' | 'none'> = {
        high: 'high',
        medium: 'medium',
        low: 'low',
      };

      // Create all issues in backend (backend auto-selects project if not provided)
      const { issuesApi } = await import('@/services/api/issues');
      const createdIssues = await Promise.all(
        extractedIssues.map((issue) =>
          issuesApi.create(workspaceId, {
            title: issue.title,
            description: issue.description,
            priority: priorityMap[issue.priority] || 'medium',
            type: 'task',
            state: 'backlog',
            labels: issue.suggestedLabels,
            sourceNoteId: noteId,
          })
        )
      );

      // Build inline issue nodes with real issue data
      const issueNodes: Array<{ type: string; attrs?: Record<string, unknown>; text?: string }> =
        [];
      createdIssues.forEach((createdIssue, index) => {
        const originalIssue = extractedIssues[index];
        issueNodes.push({
          type: 'inlineIssue',
          attrs: {
            issueId: createdIssue.id,
            issueKey: createdIssue.identifier,
            title: createdIssue.title,
            type: createdIssue.type || 'task',
            state: createdIssue.state,
            priority: createdIssue.priority,
            sourceBlockId: originalIssue?.sourceBlockId || null,
            isNew: true,
          },
        });
        // Add space between issues
        issueNodes.push({ type: 'text', text: ' ' });
      });

      // Insert at stored position or end of document
      const insertPos = extractionInsertPos ?? currentEditor.state.doc.content.size;
      currentEditor.chain().focus().insertContentAt(insertPos, issueNodes).run();

      toast.success(`Created ${createdIssues.length} issues`);
      setExtractedIssues([]);
      setShowExtractionPanel(false);
      setExtractionInsertPos(null);
    } catch (err) {
      console.error('Failed to insert issues:', err);
      toast.error('Failed to add issues to note');
    }
  }, [extractedIssues, extractionInsertPos, workspaceId, noteId]);

  const handleDismissIssue = useCallback((issueId: string) => {
    setExtractedIssues((prev) => prev.filter((i) => i.id !== issueId));
  }, []);

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
            onExtractIssue={handleExtractIssues}
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

        {/* Ask Pilot Input - Fixed at bottom of canvas */}
        <AskPilotInput
          noteId={noteId}
          workspaceId={workspaceId}
          onSubmit={async (question) => {
            toast.info(
              `Asking Pilot: "${question.substring(0, 50)}${question.length > 50 ? '...' : ''}"`
            );
            // TODO: Integrate with AI service
          }}
          className="border-t border-border"
        />
      </div>

      {/* Right Panel: Issue Extraction or Pilot Suggestions */}
      <AnimatePresence mode="wait">
        {showExtractionPanel ? (
          /* Issue Extraction Panel - Show when extracting issues */
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
                  onClick={() => setShowExtractionPanel(false)}
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
                    'w-full max-w-[320px] sm:max-w-[360px]',
                    'bg-background border-l border-border shadow-xl'
                  )}
                >
                  {/* Close button for mobile */}
                  <div className="absolute top-3 right-3 z-10">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setShowExtractionPanel(false)}
                      className="h-8 w-8 rounded-full"
                    >
                      <X className="h-4 w-4" />
                      <span className="sr-only">Close extraction panel</span>
                    </Button>
                  </div>
                  <div className="h-full overflow-hidden">
                    <IssueExtractionPanel
                      issues={extractedIssues}
                      isExtracting={isExtracting}
                      onCreateIssue={handleCreateIssue}
                      onCreateAll={handleCreateAllIssues}
                      onDismiss={handleDismissIssue}
                    />
                  </div>
                </motion.aside>
              </>
            ) : (
              <motion.aside
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: isLargeDesktop ? 340 : 288, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className="hidden lg:flex flex-shrink-0 overflow-hidden border-l border-border"
              >
                <div className={cn('h-full', isLargeDesktop ? 'w-[340px]' : 'w-72')}>
                  <div className="flex items-center justify-between p-2 border-b border-border">
                    <span className="text-sm font-medium">Issue Extraction</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setShowExtractionPanel(false)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <IssueExtractionPanel
                    issues={extractedIssues}
                    isExtracting={isExtracting}
                    onCreateIssue={handleCreateIssue}
                    onCreateAll={handleCreateAllIssues}
                    onDismiss={handleDismissIssue}
                  />
                </div>
              </motion.aside>
            )}
          </>
        ) : !isSuggestionsCollapsed ? (
          /* Pilot Suggestions - Desktop sidebar or Mobile overlay */
          <>
            {/* Mobile/Tablet: Full-screen overlay */}
            {isSmallScreen ? (
              <>
                {/* Backdrop */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
                  onClick={() => setIsSuggestionsCollapsed(true)}
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
                    'w-full max-w-[320px] sm:max-w-[360px]',
                    'bg-background border-l border-border shadow-xl'
                  )}
                >
                  {/* Close button for mobile */}
                  <div className="absolute top-3 right-3 z-10">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setIsSuggestionsCollapsed(true)}
                      className="h-8 w-8 rounded-full"
                    >
                      <X className="h-4 w-4" />
                      <span className="sr-only">Close suggestions</span>
                    </Button>
                  </div>
                  <div className="h-full overflow-hidden">
                    <MarginAnnotations
                      annotations={annotations}
                      editor={editor}
                      isCollapsed={isSuggestionsCollapsed}
                      onToggleCollapse={() => setIsSuggestionsCollapsed(!isSuggestionsCollapsed)}
                      onAnnotationClick={handleAnnotationClick}
                      onAccept={handleAnnotationAccept}
                      onReject={handleAnnotationReject}
                      onDismiss={handleAnnotationDismiss}
                    />
                  </div>
                </motion.aside>
              </>
            ) : (
              /* Desktop: Side-by-side panel - wider on ultra-large screens */
              <motion.aside
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: isLargeDesktop ? 340 : 288, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: 'easeInOut' }}
                className="hidden lg:flex flex-shrink-0 overflow-hidden h-full"
              >
                <div
                  className={cn('h-full overflow-hidden', isLargeDesktop ? 'w-[340px]' : 'w-72')}
                >
                  <MarginAnnotations
                    annotations={annotations}
                    editor={editor}
                    isCollapsed={isSuggestionsCollapsed}
                    onToggleCollapse={() => setIsSuggestionsCollapsed(!isSuggestionsCollapsed)}
                    onAnnotationClick={handleAnnotationClick}
                    onAccept={handleAnnotationAccept}
                    onReject={handleAnnotationReject}
                    onDismiss={handleAnnotationDismiss}
                  />
                </div>
              </motion.aside>
            )}
          </>
        ) : null}
      </AnimatePresence>

      {/* Collapsed Suggestions indicator - Responsive */}
      {isSuggestionsCollapsed && (
        <>
          {/* Desktop: Vertical edge toggle */}
          <div className="hidden lg:flex flex-shrink-0 border-l border-border bg-ai-muted/20">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsSuggestionsCollapsed(false)}
                  className="h-full w-10 rounded-none text-ai hover:text-ai hover:bg-ai-muted/50"
                >
                  <span className="writing-mode-vertical text-xs font-medium">Suggestions</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">Show suggestions</TooltipContent>
            </Tooltip>
          </div>

          {/* Mobile/Tablet: Floating action button */}
          <div className="lg:hidden fixed bottom-20 right-4 z-30">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="default"
                  size="icon"
                  onClick={() => setIsSuggestionsCollapsed(false)}
                  className={cn(
                    'h-12 w-12 rounded-full shadow-lg',
                    'bg-primary hover:bg-primary/90',
                    'text-primary-foreground'
                  )}
                >
                  <Sparkles className="h-5 w-5" />
                  <span className="sr-only">Show suggestions</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">Show Pilot suggestions</TooltipContent>
            </Tooltip>
          </div>
        </>
      )}

      {/* ChatView Sidebar - Toggleable right panel for conversational AI */}
      <AnimatePresence mode="wait">
        {isChatViewOpen && (
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
                    <ChatView store={aiStore.pilotSpace} />
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
                  <div className="flex items-center justify-between p-2 border-b border-border">
                    <span className="text-sm font-medium">PilotSpace AI</span>
                    <Button variant="ghost" size="icon-sm" onClick={() => setIsChatViewOpen(false)}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <ChatView store={aiStore.pilotSpace} className="h-[calc(100%-48px)]" />
                </div>
              </motion.aside>
            )}
          </>
        )}
      </AnimatePresence>

      {/* ChatView Toggle Button - Floating action button */}
      {!isChatViewOpen && (
        <div className="fixed bottom-4 right-4 z-30">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="default"
                size="icon"
                onClick={() => setIsChatViewOpen(true)}
                className={cn(
                  'h-12 w-12 rounded-full shadow-lg',
                  'bg-primary hover:bg-primary/90',
                  'text-primary-foreground'
                )}
              >
                <MessageSquare className="h-5 w-5" />
                <span className="sr-only">Open ChatView</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">Open PilotSpace AI (Cmd+Shift+P)</TooltipContent>
          </Tooltip>
        </div>
      )}
    </div>
  );
});

export default NoteCanvas;
