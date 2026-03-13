'use client';

/**
 * Note Detail Page - T114
 * Loads note via NoteStore, renders NoteCanvas, handles 404
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter, useParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { motion } from 'motion/react';
import { FileX, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { NoteCanvas } from '@/components/editor/NoteCanvas';
import { PageBreadcrumb } from '@/components/editor/PageBreadcrumb';
import { VersionHistoryPanel, type NoteVersion } from '@/components/editor/VersionHistoryPanel';
import { useNote, useUpdateNote, useAutoSave, useProjectPageTree } from '@/features/notes/hooks';
import { projectTreeKeys } from '@/features/notes/hooks/useProjectPageTree';
import { personalPagesKeys } from '@/features/notes/hooks/usePersonalPages';
import { useDeleteNote } from '@/features/notes/hooks/useDeleteNote';
import { useTogglePin } from '@/hooks/useTogglePin';
import { useNoteVersions, useRestoreNoteVersion } from '@/hooks/useNoteVersions';
import { useNoteStore } from '@/stores/RootStore';
import { useWorkspace } from '@/components/workspace-guard';
import { useProjects, selectAllProjects } from '@/features/projects/hooks/useProjects';
import { getAncestors, flattenTree } from '@/lib/tree-utils';
import { notesApi } from '@/services/api';
import { notesKeys } from '@/features/notes/hooks';
import type { JSONContent } from '@/types';

/**
 * Strips propertyBlock nodes from TipTap content to prevent unknown node errors
 * when non-issue pages are opened in NoteCanvas.
 *
 * See: RESEARCH.md Pattern 5 and STATE.md concern about editor coupling.
 */
function sanitizeNoteContent(content: JSONContent | undefined): JSONContent | undefined {
  if (!content?.content) return content;
  return {
    ...content,
    content: content.content.filter((node) => {
      const attrs = node.attrs as Record<string, unknown> | undefined;
      return !(node.type === 'propertyBlock' || attrs?.['data-property-block']);
    }),
  };
}

// Using useParams() hook instead of props for reliable client-side navigation

/**
 * Loading skeleton for the note detail page
 */
function NoteDetailSkeleton() {
  return (
    <div className="flex h-full flex-col">
      {/* Header skeleton */}
      <div className="border-b border-border">
        <div className="px-6 py-2">
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="flex items-start justify-between gap-4 px-6 py-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-8 w-3/4" />
            <div className="flex items-center gap-4">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-24" />
            </div>
            <div className="flex items-center gap-3">
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-9 w-9 rounded-md" />
            <Skeleton className="h-9 w-9 rounded-md" />
          </div>
        </div>
      </div>

      {/* Editor skeleton */}
      <div className="flex-1 p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    </div>
  );
}

/**
 * 404 Not Found component
 */
function NoteNotFound({ workspaceSlug }: { workspaceSlug: string }) {
  const router = useRouter();

  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center text-center"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
          <FileX className="h-8 w-8 text-muted-foreground" />
        </div>
        <h1 className="text-2xl font-semibold text-foreground mb-2">Note not found</h1>
        <p className="text-muted-foreground mb-6 max-w-sm">
          The note you&apos;re looking for doesn&apos;t exist or has been deleted.
        </p>
        <Button onClick={() => router.push(`/${workspaceSlug}/notes`)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Notes
        </Button>
      </motion.div>
    </div>
  );
}
/**
 * Note Detail Page Component
 */
const NoteDetailPage = observer(function NoteDetailPage() {
  const params = useParams<{ workspaceSlug: string; noteId: string }>();
  const workspaceSlug = params.workspaceSlug ?? '';
  const noteId = params.noteId ?? '';
  const router = useRouter();
  const queryClient = useQueryClient();
  const noteStore = useNoteStore();

  // Get workspace from WorkspaceGuard context (guaranteed to be loaded)
  const { workspace } = useWorkspace();

  // Ref-based content tracking to avoid re-renders on every keystroke.
  // Only the saveVersion counter (a number) lives in state to trigger debounced auto-save.
  const contentRef = useRef<JSONContent | null>(null);
  const [saveVersion, setSaveVersion] = useState(0);
  const [contentInitialized, setContentInitialized] = useState(false);

  // Get workspace ID from context (preferred) or workspaceSlug fallback
  const workspaceId = workspace?.id ?? workspaceSlug;

  // Check if params are available (used for conditional rendering later, not early return)
  const hasValidParams = !!workspaceSlug && !!noteId;

  // Fetch note data - always call hooks unconditionally
  const {
    data: note,
    isLoading: isLoadingNote,
    error: noteError,
  } = useNote({
    workspaceId,
    noteId,
    enabled: hasValidParams,
  });

  // Fetch project tree — shares same TanStack Query cache key as sidebar (no duplicate fetch).
  // Returns PageTreeNode[] (post-select tree structure); enabled only for project pages.
  const { data: treeData } = useProjectPageTree(
    workspaceId,
    note?.projectId ?? '',
    !!note?.projectId
  );

  // Fetch projects for breadcrumb project name display — shares cache with sidebar.
  const { data: projectsData } = useProjects({ workspaceId, enabled: !!note?.projectId });
  const projects = selectAllProjects(projectsData);

  // Derive breadcrumb ancestors by flattening tree then walking parentId chain (root-first).
  const ancestors = useMemo(() => {
    if (!treeData || !note?.id) return [];
    const flatNotes = flattenTree(treeData);
    return getAncestors(note.id, flatNotes);
  }, [treeData, note?.id]);

  // Get project name for breadcrumb root segment.
  const projectName = useMemo(() => {
    if (!note?.projectId) return undefined;
    return projects.find((p) => p.id === note.projectId)?.name;
  }, [note?.projectId, projects]);

  // Memoize sanitized content to avoid creating a new object reference on every render.
  // sanitizeNoteContent returns a new object each call; memoizing prevents NoteCanvas from
  // seeing unnecessary content reference changes between unrelated state updates.
  const sanitizedContent = useMemo(() => sanitizeNoteContent(note?.content), [note?.content]);

  // Track previous noteId to detect navigation
  const prevNoteIdRef = useRef<string | null>(null);
  // Flag to enable autosave only after content is initialized AND baseline is set
  const [isAutosaveReady, setIsAutosaveReady] = useState(false);

  // Reset state when noteId changes
  useEffect(() => {
    if (prevNoteIdRef.current !== null && prevNoteIdRef.current !== noteId) {
      // Note changed, reset everything
      contentRef.current = null;
      setContentInitialized(false);
      setSaveVersion(0);
      setIsAutosaveReady(false);
    }
    prevNoteIdRef.current = noteId;
  }, [noteId]);

  // Initialize content ref when note loads (no re-render triggered).
  // Sanitize content to strip propertyBlock nodes — prevents unknown node errors
  // when non-issue pages (which lack PropertyBlockExtension) open in NoteCanvas.
  useEffect(() => {
    if (note?.content && !contentInitialized) {
      contentRef.current = sanitizeNoteContent(note.content) ?? null;
      setContentInitialized(true);
    }
  }, [note?.content, contentInitialized]);

  // Note: Annotations are fetched by NoteCanvas via MobX store (aiStore.marginAnnotation)
  // to prevent duplicate API requests

  // Update note mutation
  const updateNote = useUpdateNote({
    workspaceId,
    noteId,
  });

  // Delete note mutation
  const deleteNote = useDeleteNote({
    workspaceId,
    onSuccess: () => {
      router.push(`/${workspaceSlug}/notes`);
    },
  });

  // Toggle pin mutation
  const togglePin = useTogglePin({ workspaceId });

  // Version history state
  const [showVersionHistory, setShowVersionHistory] = useState(false);

  // Fetch versions when panel is open
  const { data: versions, isLoading: isLoadingVersions } = useNoteVersions({
    workspaceId,
    noteId,
    enabled: showVersionHistory && !!note,
  });

  // Restore version mutation
  const restoreVersion = useRestoreNoteVersion({
    workspaceId,
    noteId,
    onSuccess: () => setShowVersionHistory(false),
  });

  // Auto-save for content - saveVersion (number) triggers debounce, content read from ref at save time.
  // This avoids re-rendering the entire component tree on every keystroke.
  const {
    status: _saveStatus,
    save: manualSave,
    reset: resetAutoSave,
  } = useAutoSave({
    data: saveVersion,
    onSave: async () => {
      const content = contentRef.current;
      if (content) {
        await updateNote.mutateAsync({ content });
      }
    },
    enabled: !!note && isAutosaveReady,
    debounceMs: 2000,
  });

  // Store resetAutoSave in ref to avoid dependency issues
  const resetAutoSaveRef = useRef(resetAutoSave);
  useEffect(() => {
    resetAutoSaveRef.current = resetAutoSave;
  }, [resetAutoSave]);

  // After content is initialized, reset autosave baseline and enable it
  // This ensures savedDataRef.current = saveVersion (0) before autosave starts watching
  useEffect(() => {
    if (contentInitialized && !isAutosaveReady) {
      // Use ref to avoid stale closure issues
      resetAutoSaveRef.current();
      // Small delay to ensure React state has settled
      const timer = setTimeout(() => {
        setIsAutosaveReady(true);
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [contentInitialized, isAutosaveReady]);

  // Set page title
  useEffect(() => {
    if (note) {
      document.title = `${note.title || 'Untitled'} - Pilot Space`;
    }
    return () => {
      document.title = 'Pilot Space';
    };
  }, [note]);

  // Update store when note loads
  useEffect(() => {
    if (note) {
      noteStore.setCurrentNote(note.id);
    }
    return () => {
      noteStore.setCurrentNote(null);
    };
  }, [note, noteStore]);

  // Handle content change - store in ref (no re-render), bump version to trigger debounced auto-save
  const handleContentChange = useCallback((content: JSONContent) => {
    contentRef.current = content;
    setSaveVersion((v) => v + 1);
  }, []);

  // Handle manual save (Cmd+S)
  const handleSave = useCallback(() => {
    manualSave();
  }, [manualSave]);

  // Handle title change
  const handleTitleChange = useCallback(
    (title: string) => {
      updateNote.mutate({ title });
    },
    [updateNote]
  );

  // Handle delete
  const handleDelete = useCallback(() => {
    deleteNote.mutate(noteId);
  }, [deleteNote, noteId]);

  // Handle pin toggle
  const handleTogglePin = useCallback(() => {
    if (note) {
      togglePin.mutate({ noteId: note.id, isPinned: note.isPinned });
    }
  }, [togglePin, note]);

  // Handle move to project
  const handleMove = useCallback(
    async (newProjectId: string | null) => {
      try {
        await notesApi.moveNote(workspaceId, noteId, newProjectId);
        queryClient.invalidateQueries({ queryKey: notesKeys.detail(workspaceId, noteId) });
        queryClient.invalidateQueries({ queryKey: notesKeys.lists() });
        toast.success(newProjectId ? 'Note moved to project' : 'Note moved to workspace root');
      } catch {
        toast.error('Failed to move note');
      }
    },
    [workspaceId, noteId, queryClient]
  );

  // Handle share
  const handleShare = useCallback(() => {
    // Open share dialog - to be implemented
    navigator.clipboard.writeText(window.location.href);
  }, []);

  // Handle export
  const handleExport = useCallback(() => {
    // Export functionality - to be implemented
  }, []);

  // Handle version history toggle
  const handleVersionHistory = useCallback(() => {
    setShowVersionHistory((prev) => !prev);
  }, []);

  // Handle emoji update — immediate (not debounced), invalidates tree cache so sidebar refreshes
  const handleEmojiChange = useCallback(
    (emoji: string | null) => {
      updateNote.mutate({ iconEmoji: emoji });
      // Invalidate the page tree so the sidebar emoji updates immediately
      if (note?.projectId) {
        void queryClient.invalidateQueries({
          queryKey: projectTreeKeys.tree(workspaceId, note.projectId),
        });
      } else {
        void queryClient.invalidateQueries({
          queryKey: personalPagesKeys.all,
        });
      }
    },
    [updateNote, queryClient, workspaceId, note?.projectId]
  );

  // Handle version restore
  const handleRestoreVersion = useCallback(
    async (version: NoteVersion) => {
      await restoreVersion.mutateAsync(version.id);
    },
    [restoreVersion]
  );

  // Loading state - also show skeleton when params are not ready
  if (!hasValidParams || isLoadingNote) {
    return <NoteDetailSkeleton />;
  }

  // 404 state
  if (noteError || !note) {
    return <NoteNotFound workspaceSlug={workspaceSlug} />;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Breadcrumb navigation — NAV-04. Only shown for project pages (note.projectId truthy). */}
      {note.projectId && (
        <div className="border-b border-border px-6 py-1.5">
          <PageBreadcrumb
            ancestors={ancestors}
            currentTitle={note.title || 'Untitled'}
            workspaceSlug={workspaceSlug}
            projectName={projectName}
          />
        </div>
      )}

      {/* Editor with merged header - Three-column layout per Prototype v4 */}
      <div className="relative flex-1 overflow-hidden">
        <NoteCanvas
          key={noteId}
          noteId={noteId}
          content={sanitizedContent}
          readOnly={false}
          onChange={handleContentChange}
          onSave={handleSave}
          workspaceId={workspaceId}
          // Merged header props per Prototype v4
          title={note.title}
          author={note.owner}
          createdAt={note.createdAt}
          updatedAt={note.updatedAt}
          wordCount={note.wordCount}
          isPinned={note.isPinned}
          isAIAssisted={note.isAIAssisted}
          topics={note.topics}
          workspaceSlug={workspaceSlug}
          onTitleChange={handleTitleChange}
          onShare={handleShare}
          onExport={handleExport}
          onDelete={handleDelete}
          onTogglePin={handleTogglePin}
          onVersionHistory={handleVersionHistory}
          onMove={handleMove}
          projectId={note.projectId}
          linkedIssues={note.linkedIssues}
          iconEmoji={note.iconEmoji}
          onEmojiChange={handleEmojiChange}
        />

        {/* Version History Panel - slides in from right */}
        {showVersionHistory && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="absolute right-0 top-0 bottom-0 w-80 border-l border-border bg-background shadow-lg z-10"
          >
            <VersionHistoryPanel
              versions={versions ?? []}
              currentVersionId={versions?.[0]?.id}
              isLoading={isLoadingVersions}
              onRestore={handleRestoreVersion}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
});

export default NoteDetailPage;
