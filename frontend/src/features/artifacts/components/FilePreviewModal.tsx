'use client';

import * as React from 'react';
import { Download, Maximize2, Minimize2, TableOfContents, X, ZoomIn, ZoomOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import dynamic from 'next/dynamic';
import { resolveRenderer, getLanguageForFile } from '../utils/mime-type-router';
import { useFileContent } from '../hooks/useFileContent';
import { DownloadFallback } from './renderers/DownloadFallback';

// Lazy-load heavy renderers — papaparse (~50KB), DOMPurify (~30KB), react-markdown
// are only loaded when the user actually opens a file preview of that type.
const MarkdownRenderer = dynamic(() =>
  import('./renderers/MarkdownRenderer').then((m) => ({ default: m.MarkdownRenderer }))
);
const TextRenderer = dynamic(() =>
  import('./renderers/TextRenderer').then((m) => ({ default: m.TextRenderer }))
);
const JsonRenderer = dynamic(() =>
  import('./renderers/JsonRenderer').then((m) => ({ default: m.JsonRenderer }))
);
const CodeRenderer = dynamic(() =>
  import('./renderers/CodeRenderer').then((m) => ({ default: m.CodeRenderer }))
);
const CsvRenderer = dynamic(() =>
  import('./renderers/CsvRenderer').then((m) => ({ default: m.CsvRenderer }))
);
const HtmlRenderer = dynamic(() =>
  import('./renderers/HtmlRenderer').then((m) => ({ default: m.HtmlRenderer }))
);
// docx-preview and mammoth reference browser APIs (window, document) on import.
// ssr: false is REQUIRED to prevent "window is not defined" errors during Next.js
// server render pass.
const DocxRenderer = dynamic(
  () => import('./renderers/DocxRenderer').then((m) => ({ default: m.DocxRenderer })),
  { ssr: false }
);
// SheetJS references browser APIs (ArrayBuffer, etc.) — ssr: false is REQUIRED.
const XlsxRenderer = dynamic(
  () => import('./renderers/XlsxRenderer').then((m) => ({ default: m.XlsxRenderer })),
  { ssr: false }
);

export interface FilePreviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifactId: string;
  filename: string;
  mimeType: string;
  signedUrl: string;
}

// ---------------------------------------------------------------------------
// Image Lightbox — gallery-style fullscreen overlay for images
// ---------------------------------------------------------------------------
function ImageLightbox({
  open,
  onOpenChange,
  filename,
  signedUrl,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filename: string;
  signedUrl: string;
}) {
  const [isZoomed, setIsZoomed] = React.useState(false);
  const [imgError, setImgError] = React.useState(false);

  // Reset state when lightbox opens
  React.useEffect(() => {
    if (open) {
      setIsZoomed(false);
      setImgError(false);
    }
  }, [open]);

  // Close on Escape
  React.useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onOpenChange(false);
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  // Prevent body scroll when open
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  const isValidUrl = (() => {
    try {
      const parsed = new URL(signedUrl);
      return (
        parsed.protocol === 'https:' ||
        (parsed.protocol === 'http:' &&
          (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1'))
      );
    } catch {
      return false;
    }
  })();

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label={`Image preview: ${filename}`}
    >
      {/* Backdrop — click to close */}
      <div
        className="absolute inset-0 bg-black/90 animate-in fade-in-0 duration-200"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Floating toolbar */}
      <div className="relative z-10 flex items-center justify-between px-4 py-3">
        <p className="text-sm font-medium text-white/80 truncate max-w-[50vw]">{filename}</p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-white/70 hover:text-white hover:bg-white/10"
            onClick={() => setIsZoomed((z) => !z)}
            aria-label={isZoomed ? 'Zoom out' : 'Zoom in'}
          >
            {isZoomed ? <ZoomOut className="size-4" /> : <ZoomIn className="size-4" />}
          </Button>

          {isValidUrl && (
            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-white/70 hover:text-white hover:bg-white/10"
              asChild
            >
              <a
                href={signedUrl}
                download={filename}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Download image"
              >
                <Download className="size-4" />
              </a>
            </Button>
          )}

          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-white/70 hover:text-white hover:bg-white/10"
            onClick={() => onOpenChange(false)}
            aria-label="Close"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Image area */}
      <div
        className={cn(
          'relative z-10 flex-1 flex items-center justify-center overflow-auto min-h-0 px-4 pb-4',
          isZoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'
        )}
        onClick={(e) => {
          // Only toggle zoom when clicking directly on the container or image
          if (e.target === e.currentTarget || (e.target as HTMLElement).tagName === 'IMG') {
            setIsZoomed((z) => !z);
          }
        }}
      >
        {imgError ? (
          <div className="text-sm text-white/60">Failed to load image</div>
        ) : (
          <img
            src={signedUrl}
            alt={filename}
            onError={() => setImgError(true)}
            draggable={false}
            className={cn(
              'rounded-lg shadow-2xl transition-all duration-300 ease-out select-none',
              isZoomed ? 'max-w-none w-auto scale-100' : 'max-w-[90vw] max-h-[85vh] object-contain'
            )}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// FilePreviewModal — unified entry point
// ---------------------------------------------------------------------------
export function FilePreviewModal({
  open,
  onOpenChange,
  artifactId: _artifactId,
  filename,
  mimeType,
  signedUrl,
}: FilePreviewModalProps) {
  const [isMaximized, setIsMaximized] = React.useState(false);
  const [docxTocOpen, setDocxTocOpen] = React.useState(false);

  // Reset maximize and ToC state whenever the modal re-opens
  React.useEffect(() => {
    if (open) {
      setIsMaximized(false);
      setDocxTocOpen(false);
    }
  }, [open]);

  const rendererType = resolveRenderer(mimeType, filename);
  const { content, isLoading, isExpired } = useFileContent(signedUrl, rendererType, open);

  // Images use the lightbox overlay instead of a Dialog
  if (rendererType === 'image') {
    return (
      <ImageLightbox
        open={open}
        onOpenChange={onOpenChange}
        filename={filename}
        signedUrl={signedUrl}
      />
    );
  }

  /** Returns true for legacy Office formats (.doc, .ppt) that cannot be parsed client-side.
   *  NOTE: .xls IS supported by SheetJS (BIFF8 format) — do NOT include it here. */
  function isLegacyOfficeFormat(fname: string): boolean {
    const ext = fname.split('.').pop()?.toLowerCase() ?? '';
    return ext === 'doc' || ext === 'ppt';
  }

  function renderContent() {
    // Download fallback: no content fetch needed
    if (rendererType === 'download') {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="unsupported" />;
    }

    // Office formats — handle before content fetch checks
    // Legacy formats (.doc, .xls, .ppt) degrade to download — cannot be parsed client-side.
    // Modern formats route to their real renderers (Phase 2-4); pptx still uses placeholder.
    if (rendererType === 'xlsx' || rendererType === 'docx' || rendererType === 'pptx') {
      if (isLegacyOfficeFormat(filename)) {
        return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="legacy" />;
      }
      // docx: real renderer available (Phase 2). Falls through to content fetch below.
      // xlsx: real renderer available (Phase 3). Falls through to content fetch below.
      // pptx: still placeholder until Phase 4.
      if (rendererType === 'pptx') {
        return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="unsupported" />;
      }
    }

    // Content-based renderers: need fetch
    if (isExpired) {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="expired" />;
    }

    if (isLoading) {
      return (
        <div
          className="flex items-center justify-center p-8"
          role="status"
          aria-label="Loading file content"
        >
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
        </div>
      );
    }

    if (!content) {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="error" />;
    }

    switch (rendererType) {
      case 'markdown':
        return <MarkdownRenderer content={content as string} />;
      case 'text':
        return <TextRenderer content={content as string} />;
      case 'json':
        return <JsonRenderer content={content as string} />;
      case 'code':
        return <CodeRenderer content={content as string} language={getLanguageForFile(filename)} />;
      case 'html-preview':
        return <HtmlRenderer content={content as string} filename={filename} />;
      case 'csv':
        return <CsvRenderer content={content as string} />;
      case 'xlsx':
        // content is ArrayBuffer for 'xlsx' renderer type (useFileContent binary branch)
        return <XlsxRenderer content={content as ArrayBuffer} />;
      case 'docx':
        // content is ArrayBuffer for 'docx' renderer type (useFileContent binary branch)
        return (
          <DocxRenderer
            content={content as ArrayBuffer}
            filename={filename}
            tocOpen={docxTocOpen}
            onTocOpenChange={setDocxTocOpen}
          />
        );
      default:
        return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="unsupported" />;
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          'flex flex-col p-0 gap-0 overflow-hidden',
          isMaximized ? 'w-[95vw] h-[95vh] max-w-none' : 'sm:max-w-3xl max-h-[85vh]'
        )}
        showCloseButton={false}
      >
        {/* Header */}
        <DialogHeader className="flex-row items-center justify-between px-4 py-3 border-b shrink-0 gap-2">
          <DialogTitle className="text-sm font-medium truncate flex-1">{filename}</DialogTitle>
          <div className="flex items-center gap-1 shrink-0">
            {/* File type badge */}
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">
              {mimeType.split('/')[1]?.toUpperCase() ?? 'FILE'}
            </span>

            {/* Download button — validates URL scheme (https always, http for localhost) */}
            {(() => {
              try {
                const parsed = new URL(signedUrl);
                const isHttps = parsed.protocol === 'https:';
                const isLocalHttp =
                  parsed.protocol === 'http:' &&
                  (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1');
                return isHttps || isLocalHttp;
              } catch {
                return false;
              }
            })() && (
              <Button variant="ghost" size="icon" className="size-8" asChild>
                <a
                  href={signedUrl}
                  download={filename}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Download file"
                >
                  <Download className="size-4" />
                </a>
              </Button>
            )}

            {/* ToC toggle — only shown for .docx files */}
            {rendererType === 'docx' && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setDocxTocOpen((o) => !o)}
                aria-label={docxTocOpen ? 'Hide table of contents' : 'Show table of contents'}
                aria-pressed={docxTocOpen}
              >
                <TableOfContents className="size-4" />
              </Button>
            )}

            {/* Maximize toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => setIsMaximized((m) => !m)}
              aria-label={isMaximized ? 'Restore size' : 'Maximize'}
            >
              {isMaximized ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
            </Button>

            {/* Close */}
            <DialogClose asChild>
              <Button variant="ghost" size="icon" className="size-8" aria-label="Close">
                <X className="size-4" />
              </Button>
            </DialogClose>
          </div>
        </DialogHeader>

        {/* Body — scrollable renderer area */}
        <div className="flex-1 overflow-auto min-h-0">{renderContent()}</div>
      </DialogContent>
    </Dialog>
  );
}
