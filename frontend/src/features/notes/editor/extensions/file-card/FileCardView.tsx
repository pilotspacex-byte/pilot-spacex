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
 * - ready (non-previewable): compact card with file type icon, filename, size, mime label
 * - ready (previewable): inline content preview card (code/markdown/csv/json)
 *
 * Inline preview is gated on FilePreviewConfigContext being present (provided by the
 * note/issue page). When no provider is present, files fall back to compact card behavior.
 */
import { useState, useCallback } from 'react';
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
import { cn } from '@/lib/utils';
import { useFileCardContext } from './FileCardContext';
import { useArtifactStore } from '@/stores';
import {
  useInlinePreviewContent,
  InlinePreviewHeader,
  SkeletonPreviewCard,
  InlineContentRenderer,
  getTruncationInfo,
} from './inline-preview';

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

  // Inline preview state — hooks must be called unconditionally (React rules of hooks)
  const { containerRef, content, isLoading, isError, rendererType, signedUrl } =
    useInlinePreviewContent(artifactId, mimeType, filename);
  const [expanded, setExpanded] = useState(false);

  // rendererType is non-null only when: (a) file is previewable type AND
  // (b) FilePreviewConfigContext.Provider is present in the tree
  const previewable = rendererType !== null && status === 'ready';

  // Stable dispatch helper for opening the full preview modal
  const dispatchPreviewEvent = useCallback(() => {
    if (!artifactId) return;
    queueMicrotask(() => {
      window.dispatchEvent(
        new CustomEvent('pilot:preview-artifact', {
          detail: { artifactId, filename, mimeType },
        })
      );
    });
  }, [artifactId, filename, mimeType]);

  // -------------------------------------------------------------------------
  // Uploading state
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // Ready state — inline preview card (previewable file types with provider)
  // -------------------------------------------------------------------------
  if (previewable) {
    const truncationInfo =
      content && rendererType ? getTruncationInfo(content, rendererType, expanded) : null;
    const showFooter = truncationInfo?.wasTruncated === true && rendererType !== 'markdown';

    return (
      <div
        ref={containerRef}
        className="rounded-lg border border-border bg-card my-1 overflow-hidden group"
        role="article"
        aria-label={`${filename} preview`}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            dispatchPreviewEvent();
          }
        }}
      >
        {/* Header bar */}
        <InlinePreviewHeader
          filename={filename}
          mimeType={mimeType}
          artifactId={artifactId ?? ''}
          signedUrl={signedUrl}
          onCopy={async () => {
            if (content && typeof content === 'string') {
              try {
                await navigator.clipboard.writeText(content);
              } catch (err) {
                console.error('Clipboard write failed:', err);
              }
            }
          }}
          onExpandToModal={dispatchPreviewEvent}
        />

        {/* Content area — click opens full modal */}
        <div
          className={cn(
            'transition-[max-height] duration-200 ease-out cursor-pointer',
            expanded ? '' : 'max-h-[300px] overflow-hidden',
            rendererType === 'markdown' && !expanded ? 'max-h-[300px] overflow-y-auto' : ''
          )}
          role="button"
          aria-label={`Open ${filename} full preview`}
          onClick={() => {
            if (!artifactId) return;
            dispatchPreviewEvent();
          }}
        >
          {isLoading && <SkeletonPreviewCard />}
          {isError && (
            <div className="p-4 text-center" role="alert">
              <p className="text-sm font-medium text-destructive">Couldn&apos;t load preview</p>
              <p className="text-xs text-muted-foreground mt-1">Click to open the full preview.</p>
            </div>
          )}
          {content && rendererType && (
            <InlineContentRenderer
              content={content}
              rendererType={rendererType}
              filename={filename}
              expanded={expanded}
              signedUrl={signedUrl}
            />
          )}
        </div>

        {/* Footer — expand/collapse link */}
        {showFooter && truncationInfo && (
          <div className="border-t border-border px-4 py-2">
            <button
              className="text-xs text-primary hover:underline"
              aria-expanded={expanded}
              onClick={(e) => {
                e.stopPropagation();
                setExpanded((prev) => {
                  if (prev) {
                    // Collapsing — scroll card into view
                    containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                  }
                  return !prev;
                });
              }}
            >
              {expanded ? 'Show less' : truncationInfo.label}
            </button>
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Ready state — compact card (non-previewable files or no context provider)
  // -------------------------------------------------------------------------
  return (
    <div
      className="flex items-center gap-3 rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors px-4 py-3 my-1 cursor-pointer select-none group"
      role="button"
      tabIndex={0}
      aria-label={`Open file: ${filename}`}
      onClick={dispatchPreviewEvent}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          dispatchPreviewEvent();
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
