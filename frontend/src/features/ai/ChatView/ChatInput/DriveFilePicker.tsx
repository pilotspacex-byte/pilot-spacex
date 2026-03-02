/**
 * DriveFilePicker — modal for browsing and importing Google Drive files.
 *
 * Supports folder navigation with breadcrumbs, live search, file selection,
 * and single-file import as a chat context attachment. Uses TanStack Query
 * (useDriveFiles) for data fetching; all Drive API calls go via attachmentsApi.
 *
 * @module features/ai/ChatView/ChatInput/DriveFilePicker
 */

import { useState, useCallback } from 'react';
import { Folder, File, Search, ChevronRight, RefreshCw } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useDriveFiles } from '../hooks/useDriveFiles';
import { attachmentsApi } from '@/services/api/attachments';
import type { DriveFileItem, AttachmentUploadResponse } from '@/types/attachments';

// ── Types ────────────────────────────────────────────────────────────────────

interface Breadcrumb {
  id: string | null;
  name: string;
}

export interface DriveFilePickerProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  sessionId?: string;
  onImported: (response: AttachmentUploadResponse) => void;
}

// ── Component ────────────────────────────────────────────────────────────────

export function DriveFilePicker({
  open,
  onClose,
  workspaceId,
  sessionId,
  onImported,
}: DriveFilePickerProps) {
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedFile, setSelectedFile] = useState<DriveFileItem | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ id: null, name: 'My Drive' }]);
  const [isImporting, setIsImporting] = useState(false);

  const { data, isLoading, isError, refetch } = useDriveFiles({
    workspaceId,
    parentId: currentFolderId ?? undefined,
    search: search || undefined,
  });

  const handleFolderClick = useCallback((folder: DriveFileItem) => {
    setCurrentFolderId(folder.id);
    setSelectedFile(null);
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
  }, []);

  const handleBreadcrumbClick = useCallback((crumb: Breadcrumb, index: number) => {
    setCurrentFolderId(crumb.id);
    setSelectedFile(null);
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
  }, []);

  const handleFileClick = useCallback((file: DriveFileItem) => {
    if (file.isFolder) return;
    setSelectedFile((prev) => (prev?.id === file.id ? null : file));
  }, []);

  const handleAddToChat = useCallback(async () => {
    if (!selectedFile || isImporting) return;

    setIsImporting(true);
    try {
      const response = await attachmentsApi.importDriveFile({
        workspace_id: workspaceId,
        file_id: selectedFile.id,
        filename: selectedFile.name,
        mime_type: selectedFile.mimeType,
        session_id: sessionId,
      });
      onImported(response);
      onClose();
    } finally {
      setIsImporting(false);
    }
  }, [selectedFile, isImporting, workspaceId, sessionId, onImported, onClose]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setSelectedFile(null);
  }, []);

  const handleClose = useCallback(() => {
    // Reset state when closing
    setCurrentFolderId(null);
    setSearch('');
    setSelectedFile(null);
    setBreadcrumbs([{ id: null, name: 'My Drive' }]);
    onClose();
  }, [onClose]);

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) handleClose();
      }}
    >
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Browse Google Drive</DialogTitle>
        </DialogHeader>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            aria-label="Search files"
            placeholder="Search files..."
            value={search}
            onChange={handleSearchChange}
            className="pl-8"
          />
        </div>

        {/* Breadcrumbs */}
        {!search && (
          <nav
            aria-label="Drive navigation"
            className="flex items-center gap-1 text-sm text-muted-foreground flex-wrap"
          >
            {breadcrumbs.map((crumb, index) => (
              <span key={`${crumb.id ?? 'root'}-${index}`} className="flex items-center gap-1">
                {index > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
                <button
                  type="button"
                  onClick={() => handleBreadcrumbClick(crumb, index)}
                  className={cn(
                    'hover:text-foreground transition-colors truncate max-w-[120px]',
                    index === breadcrumbs.length - 1 && 'text-foreground font-medium'
                  )}
                  disabled={index === breadcrumbs.length - 1}
                >
                  {crumb.name}
                </button>
              </span>
            ))}
          </nav>
        )}

        {/* File list */}
        <ScrollArea className="h-64 rounded-md border">
          {isLoading && (
            <div className="p-2 space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  data-testid="drive-file-skeleton"
                  className="flex items-center gap-2 px-2 py-1.5"
                >
                  <Skeleton className="h-4 w-4 shrink-0" />
                  <Skeleton className="h-4 flex-1" />
                </div>
              ))}
            </div>
          )}

          {isError && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full gap-2 p-4 text-sm text-muted-foreground">
              <span>Failed to load files.</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void refetch()}
                className="gap-1.5"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            </div>
          )}

          {!isLoading && !isError && data && (
            <>
              {data.files.length === 0 ? (
                <div className="flex items-center justify-center h-full p-4 text-sm text-muted-foreground">
                  No files found.
                </div>
              ) : (
                <div className="p-1">
                  {data.files.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        if (item.isFolder) {
                          handleFolderClick(item);
                        } else {
                          handleFileClick(item);
                        }
                      }}
                      className={cn(
                        'w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm',
                        'text-left transition-colors hover:bg-accent',
                        !item.isFolder && selectedFile?.id === item.id && 'bg-accent'
                      )}
                      data-selected={!item.isFolder && selectedFile?.id === item.id}
                    >
                      {item.isFolder ? (
                        <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <File className="h-4 w-4 shrink-0 text-muted-foreground" />
                      )}
                      <span className="truncate flex-1">{item.name}</span>
                      {item.isFolder && (
                        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </ScrollArea>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground truncate">
            {selectedFile ? selectedFile.name : 'No file selected'}
          </span>
          <div className="flex gap-2 shrink-0">
            <Button type="button" variant="ghost" onClick={handleClose} disabled={isImporting}>
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => void handleAddToChat()}
              disabled={!selectedFile || isImporting}
              aria-label="Add to chat"
            >
              {isImporting ? 'Adding...' : 'Add to chat'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

DriveFilePicker.displayName = 'DriveFilePicker';
