'use client';

/**
 * EditorLayout — 3-panel resizable IDE layout.
 *
 * Panels:
 * 1. Left: FileTree (defaultSize=20%, minSize=0, maxSize=30%, collapsible)
 * 2. Center: BreadcrumbBar (36px) + TabBar (36px, progressive) + Monaco/DiffViewer (flex) + StatusBar (22px)
 * 3. Right: SourceControlPanel (defaultSize=0, collapsible, toggle via Ctrl+Shift+G)
 *
 * Features:
 * - ResizablePanelGroup from shadcn/ui wrapper for react-resizable-panels v4
 * - Dynamic Monaco import with ssr:false + Skeleton loading
 * - MonacoErrorBoundary wraps editor
 * - observer() safe here (no TipTap in this tree)
 * - useAutoSaveEditor: 2s debounce + Cmd+S flush via file-editor:request-save
 * - Mobile (<768px): read-only CodeRenderer fallback (no Monaco)
 * - Tablet (768-1023px): Monaco with minimap disabled
 * - beforeunload warning when dirty files
 * - CSS custom properties for IDE spacing
 * - Monaco pre-warm via requestIdleCallback
 * - Ctrl+Shift+G: toggle right SourceControlPanel
 * - Clicking changed file in SourceControlPanel opens DiffViewer in center panel
 * - useProjectGitIntegration provides owner/repo from workspace integration config
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { observer } from 'mobx-react-lite';
import { Skeleton } from '@/components/ui/skeleton';
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable';
import type { PanelImperativeHandle } from 'react-resizable-panels';
import { useFileStore, useGitStore } from '@/stores/RootStore';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useAutoSaveEditor } from '../hooks/useAutoSaveEditor';
import { FileTree } from './FileTree';
import { TabBar } from './TabBar';
import { BreadcrumbBar } from './BreadcrumbBar';
import { StatusBar } from './StatusBar';
import { WelcomePane } from './WelcomePane';
import { MonacoErrorBoundary } from './ErrorBoundary';
import { SourceControlPanel } from '../panels/SourceControlPanel';
import { useProjectGitIntegration } from '../hooks/useProjectGitIntegration';
import { apiClient } from '@/services/api/client';
import type { Artifact } from '@/types/artifact';
import type { ChangedFile } from '../git-types';
import { getLanguageFromPath } from '../hooks/useFileDiff';
import { getLanguageLabel } from '../types';

// ─── CSS Custom Properties ────────────────────────────────────────────────────
// These are injected inline on the layout root element:
// --spacing-ide-gutter: 8px
// --spacing-ide-item-y: 4px
// --filetree-item-height: 28px
// --tab-height: 36px
// --status-bar-height: 22px

// ─── Dynamic Imports ──────────────────────────────────────────────────────────

const MonacoFileEditor = dynamic(() => import('./MonacoFileEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

// DiffViewer — dynamic import with ssr:false (uses monaco-editor DOM APIs)
const DiffViewer = dynamic(() => import('./DiffViewer'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

// CodeRenderer for mobile read-only fallback
const CodeRenderer = dynamic(
  () =>
    import('@/features/artifacts/components/renderers/CodeRenderer').then((m) => ({
      default: m.CodeRenderer,
    })),
  { ssr: false, loading: () => <Skeleton className="h-full w-full" /> }
);

// ─── Types ────────────────────────────────────────────────────────────────────

type RightPanelMode = 'hidden' | 'source-control';

interface DiffViewState {
  filePath: string;
  originalContent: string;
  modifiedContent: string;
  language: string;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface EditorLayoutProps {
  projectId: string;
  workspaceSlug?: string;
  workspaceId: string;
  artifacts: Artifact[];
  /** Initial file path to open on mount (from [...filePath] catch-all route). */
  initialFilePath?: string;
  className?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export const EditorLayout = observer(function EditorLayout({
  projectId,
  workspaceId,
  artifacts,
  initialFilePath,
  className,
}: EditorLayoutProps) {
  const fileStore = useFileStore();
  const gitStore = useGitStore();
  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(max-width: 1023px)');

  // ─── Git integration ─────────────────────────────────────────────────────
  const { owner, repo, isConnected } = useProjectGitIntegration(projectId, workspaceId);

  // ─── Right panel state ───────────────────────────────────────────────────
  const [rightPanelMode, setRightPanelMode] = useState<RightPanelMode>('hidden');
  const rightPanelRef = useRef<PanelImperativeHandle | null>(null);

  // ─── Diff view state ─────────────────────────────────────────────────────
  const [diffView, setDiffView] = useState<DiffViewState | null>(null);

  const [cursorLine] = useState(1);
  const [cursorCol] = useState(1);

  // ─── Wire GitStore when integration resolves ─────────────────────────────
  useEffect(() => {
    if (isConnected && owner && repo) {
      gitStore.setRepoInfo(owner, repo);
    }
  }, [isConnected, owner, repo, gitStore]);

  // ─── Expand/collapse right panel imperatively ────────────────────────────
  const toggleRightPanel = useCallback(() => {
    setRightPanelMode((prev) => {
      const next = prev === 'hidden' ? 'source-control' : 'hidden';
      if (next === 'source-control') {
        rightPanelRef.current?.expand();
      } else {
        rightPanelRef.current?.collapse();
      }
      return next;
    });
  }, []);

  // ─── Keyboard shortcuts ──────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const platform =
        (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
          ?.platform ?? navigator.platform;
      const isMac = /mac/i.test(platform);
      const modifier = isMac ? e.metaKey : e.ctrlKey;

      // Ctrl+Shift+G — toggle Source Control panel
      if (modifier && e.shiftKey && (e.key === 'g' || e.key === 'G')) {
        if (!isConnected) return;
        e.preventDefault();
        toggleRightPanel();
      }

      // Ctrl+Shift+D — view unsaved changes diff for active file
      if (modifier && e.shiftKey && (e.key === 'd' || e.key === 'D')) {
        e.preventDefault();
        const active = fileStore.activeFile;
        if (active?.isDirty && active.originalContent != null && active.content != null) {
          setDiffView({
            filePath: active.path,
            originalContent: active.originalContent,
            modifiedContent: active.content,
            language: active.language,
          });
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [isConnected, toggleRightPanel, fileStore]);

  // ─── Listen for view-diff custom event from BreadcrumbBar ─────────────────
  useEffect(() => {
    const handleViewDiff = (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        filePath: string;
        language: string;
        originalContent: string;
        modifiedContent: string;
      } | undefined;
      if (!detail) return;
      setDiffView({
        filePath: detail.filePath,
        originalContent: detail.originalContent,
        modifiedContent: detail.modifiedContent,
        language: detail.language,
      });
    };
    window.addEventListener('file-editor:view-diff', handleViewDiff);
    return () => window.removeEventListener('file-editor:view-diff', handleViewDiff);
  }, []);

  // ─── Open diff view when clicking a changed file ─────────────────────────
  const handleDiffFileSelect = useCallback(
    async (changedFile: ChangedFile) => {
      if (!owner || !repo || !gitStore.defaultBranch || !gitStore.currentBranch) return;

      const language = getLanguageFromPath(changedFile.path);

      // Fetch original content (base branch)
      let originalContent = '';
      let modifiedContent = '';

      try {
        if (changedFile.status !== 'added') {
          const res = await apiClient.get<{ content: string }>(
            `/workspaces/${workspaceId}/git/repos/${owner}/${repo}/contents/${encodeURIComponent(changedFile.path)}?ref=${encodeURIComponent(gitStore.defaultBranch)}`
          );
          originalContent = res.content ?? '';
        }
        if (changedFile.status !== 'deleted') {
          const res = await apiClient.get<{ content: string }>(
            `/workspaces/${workspaceId}/git/repos/${owner}/${repo}/contents/${encodeURIComponent(changedFile.path)}?ref=${encodeURIComponent(gitStore.currentBranch!)}`
          );
          modifiedContent = res.content ?? '';
        }
      } catch {
        // Content fetch failed — fall back to patch-based rendering
      }

      setDiffView({
        filePath: changedFile.path,
        originalContent,
        modifiedContent,
        language,
      });
    },
    [owner, repo, workspaceId, gitStore.defaultBranch, gitStore.currentBranch]
  );

  const handleCloseDiff = useCallback(() => {
    setDiffView(null);
  }, []);

  // ─── Save function ───────────────────────────────────────────────────────
  const saveFile = useCallback(
    async (fileId: string, content: string) => {
      await apiClient.put(
        `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${fileId}/content`,
        { content }
      );
    },
    [workspaceId, projectId]
  );

  // ─── Auto-save hook ──────────────────────────────────────────────────────
  const activeFileId = fileStore.activeFile?.id ?? null;
  const activeContent = fileStore.activeFile?.content ?? '';

  const { isSaving } = useAutoSaveEditor(
    activeFileId,
    activeContent,
    saveFile
  );

  // ─── Content change handler ──────────────────────────────────────────────
  const handleContentChange = useCallback(
    (value: string) => {
      if (!activeFileId) return;
      fileStore.updateContent(activeFileId, value);
      fileStore.markDirty(activeFileId);
    },
    [activeFileId, fileStore]
  );

  // ─── File select from tree ───────────────────────────────────────────────
  const handleFileSelect = useCallback(
    (artifact: Artifact) => {
      // Close diff view when selecting a regular file
      setDiffView(null);

      fileStore.openFile({
        id: artifact.id,
        name: artifact.filename,
        path: artifact.filename,
        language: getLanguageLabel(artifact.filename),
        isDirty: false,
        content: null, // content loaded lazily
        lastAccessed: Date.now(),
      });

      // Load file content asynchronously
      void (async () => {
        try {
          const res = await apiClient.get<{ content: string; filename: string; content_type: string }>(
            `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifact.id}/content`
          );
          fileStore.updateContent(artifact.id, res.content);
        } catch {
          // Content load failed — keep null, editor shows empty state
        }
      })();
    },
    [fileStore, workspaceId, projectId]
  );

  // ─── Auto-open initial file ──────────────────────────────────────────────
  useEffect(() => {
    if (!initialFilePath || artifacts.length === 0) return;
    const artifact = artifacts.find((a) => a.filename === initialFilePath);
    if (artifact) {
      handleFileSelect(artifact);
    }
  }, [initialFilePath, artifacts, handleFileSelect]);

  // ─── Monaco pre-warm ─────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(() => {
        void import('@monaco-editor/react');
      });
    } else {
      // Fallback for Safari (no requestIdleCallback)
      const timeout = setTimeout(() => {
        void import('@monaco-editor/react');
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, []);

  // ─── beforeunload guard for dirty files ──────────────────────────────────
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (fileStore.hasDirtyFiles) {
        e.preventDefault();
        // Modern browsers ignore custom message, just show generic dialog
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [fileStore]);

  const activeFile = fileStore.activeFile;

  // ─── Mobile fallback ─────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <div
        className="flex h-full flex-col"
        style={{
          // CSS custom properties for IDE spacing
          ['--spacing-ide-gutter' as string]: '8px',
          ['--spacing-ide-item-y' as string]: '4px',
          ['--filetree-item-height' as string]: '28px',
          ['--tab-height' as string]: '36px',
          ['--status-bar-height' as string]: '22px',
        }}
      >
        <div className="flex items-center justify-center h-16 border-b border-border px-4">
          <p className="text-sm text-muted-foreground text-center">
            Code editor is not available on mobile.
            <br />
            Visit on desktop for the full IDE experience.
          </p>
        </div>
        {activeFile && activeFile.content !== null && (
          <div className="flex-1 overflow-auto p-4">
            <CodeRenderer content={activeFile.content} language={activeFile.language} />
          </div>
        )}
      </div>
    );
  }

  // ─── Desktop / Tablet layout ──────────────────────────────────────────────
  return (
    <div
      className={`flex h-full flex-col ${className ?? ''}`}
      style={{
        ['--spacing-ide-gutter' as string]: '8px',
        ['--spacing-ide-item-y' as string]: '4px',
        ['--filetree-item-height' as string]: '28px',
        ['--tab-height' as string]: '36px',
        ['--status-bar-height' as string]: '22px',
      }}
    >
      <ResizablePanelGroup orientation="horizontal" className="flex-1">
        {/* ── Left: FileTree ─────────────────────────────────────────── */}
        <ResizablePanel
          id="code-filetree"
          defaultSize={isTablet ? '0%' : '25%'}
          minSize="15%"
          maxSize="40%"
          collapsible
          className="min-w-0"
        >
          <FileTree
            artifacts={artifacts}
            onFileSelect={handleFileSelect}
            projectId={projectId}
            className="h-full"
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* ── Center: Editor / DiffViewer ─────────────────────────── */}
        <ResizablePanel id="code-editor" defaultSize={isTablet ? '100%' : '75%'} minSize="40%" className="min-w-0">
          <div className="flex h-full flex-col">
            {/* Breadcrumb bar — hidden on mobile via CSS in BreadcrumbBar */}
            <BreadcrumbBar />

            {/* Tab bar — progressive disclosure (null when empty) */}
            <TabBar />

            {/* Editor / DiffViewer content */}
            <div className="relative flex-1 overflow-hidden">
              {diffView ? (
                /* DiffViewer mode — shown when a changed file is selected in SourceControlPanel */
                <MonacoErrorBoundary>
                  <DiffViewer
                    filePath={diffView.filePath}
                    originalContent={diffView.originalContent}
                    modifiedContent={diffView.modifiedContent}
                    language={diffView.language}
                    onClose={handleCloseDiff}
                  />
                </MonacoErrorBoundary>
              ) : activeFile ? (
                <MonacoErrorBoundary>
                  {activeFile.content !== null ? (
                    <MonacoFileEditor
                      fileId={activeFile.id}
                      content={activeFile.content}
                      language={activeFile.language}
                      onChange={handleContentChange}
                      onSave={() => {
                        window.dispatchEvent(new CustomEvent('file-editor:request-save'));
                      }}
                    />
                  ) : (
                    // Content loading skeleton
                    <Skeleton className="h-full w-full" />
                  )}
                </MonacoErrorBoundary>
              ) : (
                <WelcomePane />
              )}
            </div>

            {/* Status bar — 22px */}
            <StatusBar
              line={cursorLine}
              col={cursorCol}
              isSaving={isSaving}
            />
          </div>
        </ResizablePanel>

        {/* ── Right: SourceControlPanel ───────────────────────────── */}
        {isConnected && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel
              id="code-source-control"
              panelRef={rightPanelRef}
              defaultSize="0%"
              minSize="25%"
              maxSize="40%"
              collapsible
              className="min-w-0"
            >
              <div className="h-full">
                {rightPanelMode === 'source-control' && (
                  <SourceControlPanel
                    workspaceId={workspaceId}
                    owner={owner}
                    repo={repo}
                    onFileSelect={handleDiffFileSelect}
                  />
                )}
              </div>
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  );
});
