'use client';

/**
 * FileCardView — Observer UI component for the FileCard node.
 *
 * This is the reactive child rendered inside FileCardNodeView (the plain NodeView wrapper).
 * It is SAFE to use observer() here because this is NOT the ReactNodeViewRenderer target
 * — it is a regular React child rendered inside the NodeViewWrapper.
 *
 * Renders three states:
 * - uploading: compact card with progress bar (reads live progress from ArtifactStore)
 * - error: card with destructive styling and retry button
 * - ready: card with file type icon, filename, size, and mime type label
 *
 * Note: The "open preview" action for ready cards is stubbed as a no-op role="button".
 * The FilePreviewModal is built in Phase 34 and will wire the click handler.
 */
import { observer } from 'mobx-react-lite';
import {
  File,
  FileText,
  FileCode,
  FileSpreadsheet,
  Image,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { useFileCardContext } from './FileCardContext';
import { useArtifactStore } from '@/stores';

/** Returns the appropriate Lucide icon component for a given MIME type. */
function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) return Image;
  if (mimeType === 'application/pdf' || mimeType.startsWith('text/')) return FileText;
  if (mimeType === 'text/csv' || mimeType.includes('spreadsheet') || mimeType.includes('excel'))
    return FileSpreadsheet;
  if (
    mimeType.includes('javascript') ||
    mimeType.includes('typescript') ||
    mimeType.includes('html') ||
    mimeType.includes('css')
  )
    return FileCode;
  return File;
}

/** Format bytes to human-readable string (e.g. "1.2 MB"). */
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export const FileCardView = observer(function FileCardView() {
  const { artifactId, filename, mimeType, sizeBytes, status, readOnly, updateAttributes } =
    useFileCardContext();
  const artifactStore = useArtifactStore();
  const progress = artifactStore.getProgress(filename);
  const FileIcon = getFileIcon(mimeType);

  if (status === 'uploading') {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3 my-1 select-none">
        <FileIcon className="h-5 w-5 shrink-0 text-muted-foreground" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate text-foreground">{filename}</p>
          <div className="mt-1.5 flex items-center gap-2">
            <Progress value={progress} className="h-1 flex-1" />
            <span className="text-xs text-muted-foreground shrink-0">{progress}%</span>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 my-1 select-none">
        <AlertCircle className="h-5 w-5 shrink-0 text-destructive" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate text-foreground">{filename}</p>
          <p className="text-xs text-destructive mt-0.5">Upload failed</p>
        </div>
        {!readOnly && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs shrink-0"
            onClick={() => updateAttributes({ status: 'uploading' })}
            aria-label="Retry upload"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Retry
          </Button>
        )}
      </div>
    );
  }

  // status === 'ready'
  return (
    <div
      className="flex items-center gap-3 rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors px-4 py-3 my-1 cursor-pointer select-none group"
      role="button"
      tabIndex={0}
      aria-label={`Open file: ${filename}`}
      onClick={() => {
        if (!artifactId) return;
        // Defer dispatch so React state updates from the event listener run outside
        // TipTap's ReactRenderer cycle (prevents residual flushSync warnings).
        queueMicrotask(() => {
          window.dispatchEvent(
            new CustomEvent('pilot:preview-artifact', {
              detail: { artifactId, filename, mimeType },
            })
          );
        });
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (!artifactId) return;
          queueMicrotask(() => {
            window.dispatchEvent(
              new CustomEvent('pilot:preview-artifact', {
                detail: { artifactId, filename, mimeType },
              })
            );
          });
        }
      }}
    >
      <FileIcon className="h-5 w-5 shrink-0 text-primary/70" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate text-foreground">{filename}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatBytes(sizeBytes)} · {mimeType.split('/')[1]?.toUpperCase() ?? 'FILE'}
        </p>
      </div>
    </div>
  );
});
