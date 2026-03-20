'use client';

/**
 * ArtifactsPage — Project artifact management page.
 *
 * MGMT-01: Table view of all project artifacts with icon, name, size, uploader, date
 * MGMT-02: FilePreviewModal on row click (signed URL fetched on demand)
 * MGMT-03: Download button opens signed URL in new tab
 * MGMT-04: Delete with shadcn AlertDialog + optimistic update (row removed instantly)
 * MGMT-05: Per-keystroke search filter by filename (case-insensitive)
 * MGMT-06: Sort dropdown — Date/Name/Size/Type — persisted in ?sort= URL param via router.replace
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
  Paperclip,
  Download,
  Trash2,
  Search,
  AlertCircle,
  FileText,
  FileImage,
  FileCode,
  FileSpreadsheet,
  File,
} from 'lucide-react';
import { useStore } from '@/stores';
import {
  useProjectArtifacts,
  useDeleteArtifact,
  useArtifactSignedUrl,
} from '@/features/artifacts/hooks';
import { FilePreviewModal } from '@/features/artifacts';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { toast } from 'sonner';
import type { Artifact } from '@/types/artifact';
import { artifactsApi } from '@/services/api/artifacts';

// ============================================================================
// Types
// ============================================================================

type SortKey = 'date' | 'name' | 'size' | 'type';

// ============================================================================
// Helper functions (module-level, pure, no hooks)
// ============================================================================

function getFileTypeIcon(mimeType: string): React.ElementType {
  if (mimeType.startsWith('image/')) return FileImage;
  if (mimeType === 'text/csv') return FileSpreadsheet;
  if (['application/json', 'application/x-yaml', 'application/javascript'].includes(mimeType))
    return FileCode;
  if (mimeType.startsWith('text/')) return FileText;
  return File;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'] as const;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatRelativeDate(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const minutes = Math.round(diff / 60000);
  if (Math.abs(minutes) < 60) return rtf.format(-minutes, 'minute');
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return rtf.format(-hours, 'hour');
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 30) return rtf.format(-days, 'day');
  const months = Math.round(days / 30);
  return rtf.format(-months, 'month');
}

function sortArtifacts(items: Artifact[], sortKey: SortKey): Artifact[] {
  return [...items].sort((a, b) => {
    switch (sortKey) {
      case 'date':
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      case 'name':
        return a.filename.localeCompare(b.filename);
      case 'size':
        return b.sizeBytes - a.sizeBytes;
      case 'type':
        return a.mimeType.localeCompare(b.mimeType);
      default:
        return 0;
    }
  });
}

// ============================================================================
// ArtifactTableSkeleton sub-component
// ============================================================================

function ArtifactTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

// ============================================================================
// ArtifactsPage — Main page component
// ============================================================================

const ArtifactsPage = observer(function ArtifactsPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  // Local UI state
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedArtifact, setSelectedArtifact] = React.useState<Artifact | null>(null);
  const [deleteTargetId, setDeleteTargetId] = React.useState<string | null>(null);

  // Sort from URL (locked decision: persisted in search params — not browser history)
  const sortKey = (searchParams.get('sort') ?? 'date') as SortKey;

  // Server state
  const {
    data: artifacts,
    isLoading,
    isError,
  } = useProjectArtifacts(workspaceId, params.projectId);

  // Signed URL — on-demand: only fetches when selectedArtifact is set
  const { data: signedUrlData } = useArtifactSignedUrl(
    workspaceId,
    params.projectId,
    selectedArtifact?.id ?? null
  );

  // Delete mutation — has optimistic update + error rollback + toast built-in
  const deleteMutation = useDeleteArtifact(workspaceId, params.projectId);

  // Client-side derived state (MGMT-05 search, MGMT-06 sort)
  const filteredSorted = React.useMemo(() => {
    let items = artifacts ?? [];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter((a) => a.filename.toLowerCase().includes(q));
    }
    return sortArtifacts(items, sortKey);
  }, [artifacts, searchQuery, sortKey]);

  // Handlers
  const handleSortChange = (newSort: SortKey) => {
    const p = new URLSearchParams(searchParams.toString());
    p.set('sort', newSort);
    router.replace(`?${p.toString()}`, { scroll: false });
  };

  const handleDownload = async (artifact: Artifact) => {
    try {
      // Use artifactsApi directly for a one-shot download (no TanStack cache needed)
      const { url } = await artifactsApi.getSignedUrl(workspaceId, params.projectId, artifact.id);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch {
      toast.error('Download failed. Please try again.');
    }
  };

  const handleDeleteConfirm = () => {
    if (!deleteTargetId) return;
    deleteMutation.mutate(deleteTargetId, {
      onSettled: () => setDeleteTargetId(null),
    });
  };

  // Error state
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16">
        <AlertCircle className="size-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Failed to load artifacts</h2>
        <p className="text-muted-foreground">Something went wrong. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center justify-between border-b px-6 py-4 gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">Artifacts</h1>
          {!isLoading && artifacts && (
            <span className="text-sm text-muted-foreground">
              {filteredSorted.length} file{filteredSorted.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Search input — MGMT-05 */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 w-48 sm:w-64"
              aria-label="Search artifacts by filename"
            />
          </div>
          {/* Sort dropdown — MGMT-06 */}
          <Select value={sortKey} onValueChange={(v) => handleSortChange(v as SortKey)}>
            <SelectTrigger className="w-[140px]" aria-label="Sort artifacts">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Newest first</SelectItem>
              <SelectItem value="name">Name A-Z</SelectItem>
              <SelectItem value="size">Largest first</SelectItem>
              <SelectItem value="type">By type</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <ArtifactTableSkeleton />
        ) : filteredSorted.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Paperclip className="size-12 text-muted-foreground/40 mb-4" />
            <h3 className="text-lg font-medium mb-1">
              {searchQuery ? 'No files match your search' : 'No artifacts yet'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {searchQuery
                ? 'Try a different search term'
                : 'Upload files in your notes to see them here'}
            </p>
          </div>
        ) : (
          /* Artifact table — MGMT-01 */
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Name</TableHead>
                <TableHead className="w-24 hidden sm:table-cell">Size</TableHead>
                <TableHead className="w-36 hidden md:table-cell">Uploaded by</TableHead>
                <TableHead className="w-32 hidden md:table-cell">Date</TableHead>
                <TableHead className="w-20 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSorted.map((artifact) => {
                const Icon = getFileTypeIcon(artifact.mimeType);
                return (
                  <TableRow
                    key={artifact.id}
                    className="cursor-pointer hover:bg-accent/50"
                    onClick={() => setSelectedArtifact(artifact)}
                  >
                    <TableCell>
                      <Icon className="size-4 text-muted-foreground" />
                    </TableCell>
                    <TableCell className="font-medium max-w-[200px] truncate">
                      {artifact.filename}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden sm:table-cell">
                      {formatBytes(artifact.sizeBytes)}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {artifact.uploader ? (
                        <div className="flex items-center gap-2">
                          <Avatar className="size-5">
                            <AvatarFallback className="text-[10px]">
                              {artifact.uploader.displayName.charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <span className="text-sm truncate max-w-[100px]">
                            {artifact.uploader.displayName}
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm hidden md:table-cell">
                      {formatRelativeDate(artifact.createdAt)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div
                        className="flex items-center justify-end gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {/* Download — MGMT-03 */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7"
                          onClick={() => void handleDownload(artifact)}
                          aria-label={`Download ${artifact.filename}`}
                        >
                          <Download className="size-3.5" />
                        </Button>
                        {/* Delete — MGMT-04 */}
                        <AlertDialog
                          open={deleteTargetId === artifact.id}
                          onOpenChange={(open) => !open && setDeleteTargetId(null)}
                        >
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-7 text-destructive hover:text-destructive"
                              onClick={() => setDeleteTargetId(artifact.id)}
                              aria-label={`Delete ${artifact.filename}`}
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete artifact?</AlertDialogTitle>
                              <AlertDialogDescription>
                                <strong>{artifact.filename}</strong> will be permanently deleted.
                                This cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                onClick={handleDeleteConfirm}
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Preview modal — MGMT-02. Render conditionally, gated by selectedArtifact state. */}
      {selectedArtifact && signedUrlData && (
        <FilePreviewModal
          open={!!selectedArtifact}
          onOpenChange={(open) => !open && setSelectedArtifact(null)}
          artifactId={selectedArtifact.id}
          filename={selectedArtifact.filename}
          mimeType={selectedArtifact.mimeType}
          signedUrl={signedUrlData.url}
        />
      )}
    </div>
  );
});

export default ArtifactsPage;
