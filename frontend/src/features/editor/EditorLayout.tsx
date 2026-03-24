'use client';

/**
 * EditorLayout - Three-panel resizable layout for the IDE editor.
 *
 * Panels:
 * 1. File tree (left) - Collapsible, 20% default (~240px), max 30% (~400px)
 * 2. Editor (center) - Fills remaining space, min 40%
 * 3. Symbol outline (right) - Conditional, 15% default, collapsible via Cmd+Shift+O
 *
 * Preview is NOT a separate panel -- it replaces editor content via toggle
 * (per UI-SPEC: "appears only in preview mode, replaces editor").
 *
 * Features:
 * - Crossfade transitions for mode/file switches (200ms opacity)
 * - Auto-save via useAutoSaveEditor (2s debounce + Cmd+S flush)
 * - QuickOpen overlay (Cmd+P) always available
 * - CommandPalette overlay (Cmd+Shift+P) always available
 * - BreadcrumbBar between TabBar and editor content
 * - SymbolOutlinePanel as conditional right panel
 * - MobX observer for reactive FileStore state
 */

import { useState, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { observer } from 'mobx-react-lite';
import { useMonaco } from '@monaco-editor/react';
import { FolderTree, GitBranch } from 'lucide-react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useFileStore, useGitWebStore, useWorkspaceStore } from '@/stores/RootStore';
import { PluginSandbox, usePluginLoader, usePluginEditorBridge } from '@/features/plugins';
import { FileTree } from '@/features/file-browser/components/FileTree';
import { TabBar } from '@/features/file-browser/components/TabBar';
import { QuickOpen } from '@/features/file-browser/components/QuickOpen';
import { CommandPalette } from '@/features/command-palette/components/CommandPalette';
import { useCommandPalette } from '@/features/command-palette/hooks/useCommandPalette';
import { BreadcrumbBar } from '@/features/breadcrumbs/components/BreadcrumbBar';
import { registerFileActions } from '@/features/command-palette/actions/fileActions';
import { registerViewActions } from '@/features/command-palette/actions/viewActions';
import { useSymbolOutline } from '@/features/symbol-outline/hooks/useSymbolOutline';
import { useFileDiff } from '@/features/source-control/hooks/useFileDiff';
import { useAutoSaveEditor } from './hooks/useAutoSaveEditor';
import { useDiagnostics } from './hooks/useDiagnostics';
import type { FileTreeItem } from '@/features/file-browser/hooks/useFileTree';
import type { DocumentSymbol } from '@/features/symbol-outline/types';

const MonacoNoteEditor = dynamic(() => import('./MonacoNoteEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

const MonacoFileEditor = dynamic(() => import('./MonacoFileEditor'), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

const SymbolOutlinePanel = dynamic(
  () =>
    import('@/features/symbol-outline/components/SymbolOutlinePanel').then((m) => ({
      default: m.SymbolOutlinePanel,
    })),
  { ssr: false, loading: () => null }
);

const DiagnosticsPanel = dynamic(
  () =>
    import('./components/DiagnosticsPanel').then((m) => ({
      default: m.DiagnosticsPanel,
    })),
  { ssr: false, loading: () => null }
);

const SourceControlPanel = dynamic(
  () =>
    import('@/features/source-control/components/SourceControlPanel').then((m) => ({
      default: m.SourceControlPanel,
    })),
  { ssr: false, loading: () => null }
);

const DiffViewer = dynamic(
  () =>
    import('@/features/source-control/components/DiffViewer').then((m) => ({
      default: m.DiffViewer,
    })),
  { ssr: false, loading: () => <Skeleton className="h-full w-full" /> }
);

/** Detect Tauri runtime (web-only SCM tab hidden on desktop). */
function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

interface EditorLayoutProps {
  fileTreeItems: FileTreeItem[];
  className?: string;
  /** Persistence callback: receives file ID and content string. Called by auto-save (2s debounce) and Cmd+S. */
  onSave?: (fileId: string, content: string) => Promise<void>;
}

/** Empty state shown when no file is open. */
function EmptyEditor() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <h2 className="text-lg font-semibold">Nothing open</h2>
      <p className="text-muted-foreground mt-2">
        Open a file from the sidebar, or press Cmd+P to search.
      </p>
    </div>
  );
}

export const EditorLayout = observer(function EditorLayout({
  fileTreeItems,
  className,
  onSave,
}: EditorLayoutProps) {
  const fileStore = useFileStore();
  const gitWebStore = useGitWebStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';
  const activeFile = fileStore.activeFile;
  const changedFileCount = gitWebStore.changedFileCount;
  const selectedDiffPath = gitWebStore.selectedFilePath;
  const selectedFileStatus = selectedDiffPath
    ? gitWebStore.changedFiles.find((f) => f.path === selectedDiffPath)?.status
    : undefined;
  const [leftPanelTab, setLeftPanelTab] = useState<'files' | 'scm'>('files');

  // Fetch diff content when a changed file is selected
  const {
    original: diffOriginal,
    modified: diffModified,
    language: diffLanguage,
    isLoading: isDiffLoading,
  } = useFileDiff(
    gitWebStore.currentRepo,
    selectedDiffPath,
    gitWebStore.currentBranch,
    gitWebStore.defaultBranch,
    selectedFileStatus
  );

  // Monaco instance + diagnostics
  const monaco = useMonaco();
  const { diagnostics, counts } = useDiagnostics(monaco);

  // Plugin system: bridge DOM events to editor and load enabled plugins
  usePluginEditorBridge(null, monaco);
  const { plugins } = usePluginLoader(workspaceId);

  // Diagnostic click-to-navigate handler
  const handleDiagnosticNavigate = useCallback(
    (uri: string, line: number, _column: number) => {
      // Check if the diagnostic belongs to the currently active file
      const activeUri = activeFile?.path ?? '';
      const diagnosticPath = uri.replace(/^(file:\/\/\/|inmemory:\/\/model\/)/, '');

      if (activeUri && diagnosticPath !== activeUri) {
        // Cross-file navigation: not yet supported without full file metadata
        console.warn('Cross-file diagnostic navigation not yet supported:', uri);
      }

      // Navigate the editor to the target line (works for same-file diagnostics)
      window.dispatchEvent(new CustomEvent('symbol-outline:navigate', { detail: { uri, line } }));
    },
    [activeFile?.path]
  );

  // Command palette state
  const { isOpen: isPaletteOpen, close: closePalette } = useCommandPalette();

  // Symbol outline panel state
  const [isOutlineOpen, setIsOutlineOpen] = useState(false);
  const toggleOutline = useCallback(() => setIsOutlineOpen((prev) => !prev), []);

  // Symbol extraction from active file content
  const { symbols, activeSymbolId } = useSymbolOutline(
    activeFile?.content ?? '',
    activeFile?.source === 'note' ? 'markdown' : (activeFile?.language ?? ''),
    null // No editor instance at layout level; cursor tracking handled inside editors
  );

  // Auto-save: delegates to parent-provided onSave callback (no-op if not provided)
  const saveFn = useCallback(
    async (id: string, content: string) => {
      if (onSave) {
        await onSave(id, content);
      }
    },
    [onSave]
  );

  useAutoSaveEditor(activeFile?.id ?? null, activeFile?.content ?? '', saveFn);

  const handleContentChange = useCallback(
    (content: string) => {
      const file = fileStore.activeFile;
      if (file) {
        fileStore.updateContent(file.id, content);
      }
    },
    [fileStore]
  );

  // Symbol click-to-navigate: dispatch DOM event for Monaco editors to consume
  const handleSelectSymbol = useCallback((symbol: DocumentSymbol) => {
    window.dispatchEvent(
      new CustomEvent('symbol-outline:navigate', { detail: { line: symbol.line } })
    );
  }, []);

  // Global Cmd+Shift+O listener (for when focus is outside Monaco)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'o') {
        e.preventDefault();
        toggleOutline();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleOutline]);

  // Listen for symbol-outline:toggle custom event (from Monaco keybinding override)
  useEffect(() => {
    function handleToggleEvent() {
      toggleOutline();
    }
    window.addEventListener('symbol-outline:toggle', handleToggleEvent);
    return () => window.removeEventListener('symbol-outline:toggle', handleToggleEvent);
  }, [toggleOutline]);

  // Register file + view actions (no editor dependency)
  useEffect(() => {
    const cleanups = [
      registerFileActions({
        saveFile: () => {
          window.dispatchEvent(new CustomEvent('issue-force-save'));
        },
        closeTab: () => {
          const active = fileStore.activeFile;
          if (active) fileStore.closeFile(active.id);
        },
        closeAllTabs: () => {
          fileStore.closeAll();
        },
      }),
      registerViewActions({
        toggleSidebar: () => {
          /* Sidebar toggle wired at workspace layout level */
        },
        togglePreview: () => {
          /* Preview toggle wired inside Monaco editors */
        },
        toggleOutline,
      }),
    ];
    return () => cleanups.forEach((fn) => fn());
  }, [fileStore, toggleOutline]);

  return (
    <div className={className}>
      <ResizablePanelGroup orientation="horizontal">
        {/* Left panel - File Tree / Source Control tabs */}
        <ResizablePanel defaultSize={20} minSize={0} maxSize={30} collapsible>
          <div className="h-full transition-all duration-200">
            <Tabs
              value={leftPanelTab}
              onValueChange={(v) => setLeftPanelTab(v as 'files' | 'scm')}
              className="h-full flex flex-col"
            >
              <TabsList className="w-full justify-start border-b rounded-none h-9 bg-transparent px-1 shrink-0">
                <TabsTrigger value="files" className="text-xs">
                  <FolderTree className="h-3.5 w-3.5 mr-1" /> Files
                </TabsTrigger>
                {!isTauri() && (
                  <TabsTrigger value="scm" className="text-xs relative">
                    <GitBranch className="h-3.5 w-3.5 mr-1" /> Source Control
                    {changedFileCount > 0 && (
                      <span className="ml-1 bg-primary text-primary-foreground rounded-full text-[10px] px-1.5 min-w-[18px] text-center">
                        {changedFileCount}
                      </span>
                    )}
                  </TabsTrigger>
                )}
              </TabsList>
              <TabsContent value="files" className="flex-1 mt-0 overflow-hidden">
                <FileTree items={fileTreeItems} className="h-full" />
              </TabsContent>
              {!isTauri() && (
                <TabsContent value="scm" className="flex-1 mt-0 overflow-hidden">
                  <SourceControlPanel />
                </TabsContent>
              )}
            </Tabs>
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Editor - center panel */}
        <ResizablePanel defaultSize={isOutlineOpen ? 65 : 80} minSize={40}>
          <div className="flex flex-col h-full">
            <TabBar />
            <BreadcrumbBar fileTreeItems={fileTreeItems} />

            {/* Crossfade transition wrapper */}
            <div className="flex-1 relative overflow-hidden">
              <div className="absolute inset-0 transition-opacity duration-200">
                {selectedDiffPath ? (
                  isDiffLoading ? (
                    <Skeleton className="h-full w-full" />
                  ) : (
                    <DiffViewer
                      originalContent={diffOriginal}
                      modifiedContent={diffModified}
                      language={diffLanguage}
                      filePath={selectedDiffPath}
                      onClose={() => gitWebStore.selectFile(null)}
                    />
                  )
                ) : activeFile ? (
                  activeFile.source === 'note' ? (
                    <MonacoNoteEditor
                      noteId={activeFile.id}
                      initialContent={activeFile.content}
                      onChange={handleContentChange}
                      isReadOnly={activeFile.isReadOnly}
                      className="h-full"
                    />
                  ) : (
                    <MonacoFileEditor file={activeFile} onChange={handleContentChange} />
                  )
                ) : (
                  <EmptyEditor />
                )}
              </div>
            </div>

            {/* Problems panel - below editor, inside center flex column */}
            <DiagnosticsPanel
              diagnostics={diagnostics}
              counts={counts}
              onNavigate={handleDiagnosticNavigate}
            />
          </div>
        </ResizablePanel>

        {/* Symbol Outline - conditional right panel */}
        {isOutlineOpen && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={15} minSize={10} maxSize={25}>
              <SymbolOutlinePanel
                isOpen={isOutlineOpen}
                onToggle={toggleOutline}
                symbols={symbols}
                activeSymbolId={activeSymbolId}
                onSelectSymbol={handleSelectSymbol}
              />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

      {/* QuickOpen overlay - always available */}
      <QuickOpen items={fileTreeItems} />

      {/* CommandPalette overlay - always available */}
      <CommandPalette isOpen={isPaletteOpen} onClose={closePalette} />

      {/* Plugin sandboxes - hidden iframes for enabled plugins */}
      {workspaceId &&
        plugins.map((p) => (
          <PluginSandbox
            key={p.manifest.name}
            manifest={p.manifest}
            jsContent={p.jsContent}
            onError={(err) => console.warn(`Plugin ${p.manifest.name} error:`, err)}
          />
        ))}
    </div>
  );
});
