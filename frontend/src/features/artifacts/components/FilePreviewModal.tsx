'use client';

import * as React from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  LayoutList,
  Maximize2,
  Minimize2,
  Play,
  TableOfContents,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useParams } from 'next/navigation';
import { observer } from 'mobx-react-lite';
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
import { useStore } from '@/stores';
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
// PptxViewJS uses Canvas API and browser globals — ssr: false is REQUIRED.
const PptxRenderer = dynamic(
  () => import('./renderers/PptxRenderer').then((m) => ({ default: m.PptxRenderer })),
  { ssr: false }
);
// PptxThumbnailStrip also uses Canvas API and IntersectionObserver — ssr: false is REQUIRED.
const PptxThumbnailStrip = dynamic(
  () => import('./renderers/PptxThumbnailStrip').then((m) => ({ default: m.PptxThumbnailStrip })),
  { ssr: false }
);
// PptxAnnotationPanel uses TanStack Query and browser APIs — ssr: false is REQUIRED.
const PptxAnnotationPanel = dynamic(
  () => import('./PptxAnnotationPanel').then((m) => ({ default: m.PptxAnnotationPanel })),
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
export const FilePreviewModal = observer(function FilePreviewModal({
  open,
  onOpenChange,
  artifactId,
  filename,
  mimeType,
  signedUrl,
}: FilePreviewModalProps) {
  // Workspace and user context — needed for annotation API calls
  const params = useParams<{ workspaceSlug?: string; projectId?: string }>();
  const { workspaceStore, authStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';
  const projectId = params.projectId ?? '';
  const currentUserId = authStore.user?.id ?? '';

  const [isMaximized, setIsMaximized] = React.useState(false);
  const [docxTocOpen, setDocxTocOpen] = React.useState(false);

  // PPTX slide navigation state — lives here (controlled component pattern)
  const [currentSlide, setCurrentSlide] = React.useState(0);
  const [slideCount, setSlideCount] = React.useState(0);
  // Thumbnail strip visibility — hidden by default to maximise slide viewing area
  const [showThumbnails, setShowThumbnails] = React.useState(false);

  // Fullscreen state — tracks browser Fullscreen API state
  const slideContainerRef = React.useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = React.useState(false);

  // Reset maximize, ToC, and PPTX slide state whenever the modal re-opens
  React.useEffect(() => {
    if (open) {
      setIsMaximized(false);
      setDocxTocOpen(false);
      setCurrentSlide(0);
      setSlideCount(0);
      setShowThumbnails(false);
    }
  }, [open]);

  // Listen for fullscreen change events (handles browser Escape key exit and external changes)
  React.useEffect(() => {
    function handleFullscreenChange() {
      setIsFullscreen(!!document.fullscreenElement);
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const toggleFullscreen = React.useCallback(() => {
    if (!slideContainerRef.current) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void slideContainerRef.current.requestFullscreen();
    }
  }, []);

  const rendererType = resolveRenderer(mimeType, filename);

  /** Legacy Office formats (.doc, .ppt) degrade to download — skip content fetch */
  const isLegacyOffice = React.useMemo(() => isLegacyOfficeFormat(filename), [filename]);

  const { content, isLoading, isExpired } = useFileContent(
    signedUrl,
    rendererType,
    open && !isLegacyOffice
  );

  // Keyboard navigation for PPTX slides — only when renderer is pptx, slides loaded,
  // modal is open, and focus is NOT inside an editable element (textarea, input, contenteditable)
  React.useEffect(() => {
    if (!open || rendererType !== 'pptx' || slideCount === 0) return;
    function handleKeyDown(e: KeyboardEvent) {
      // Skip if focus is inside an editable element (annotation textarea, search input, etc.)
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'TEXTAREA' || tag === 'INPUT' || (e.target as HTMLElement)?.isContentEditable)
        return;
      if (e.key === 'ArrowLeft' && currentSlide > 0) {
        setCurrentSlide((s) => s - 1);
      } else if (e.key === 'ArrowRight' && currentSlide < slideCount - 1) {
        setCurrentSlide((s) => s + 1);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, rendererType, currentSlide, slideCount]);

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

    // Legacy Office formats (.doc, .ppt) degrade to download — cannot be parsed client-side.
    if (isLegacyOffice) {
      return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="legacy" />;
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
        return (
          <XlsxRenderer
            content={content as ArrayBuffer}
            filename={filename}
            signedUrl={signedUrl}
          />
        );
      case 'docx':
        // content is ArrayBuffer for 'docx' renderer type (useFileContent binary branch)
        return (
          <DocxRenderer
            content={content as ArrayBuffer}
            filename={filename}
            signedUrl={signedUrl}
            tocOpen={docxTocOpen}
            onTocOpenChange={setDocxTocOpen}
          />
        );
      case 'pptx':
        // content is ArrayBuffer for 'pptx' renderer type (useFileContent binary branch)
        return (
          <div className="flex h-full">
            {/* Thumbnail sidebar — left; hidden in fullscreen for clean slide-only view */}
            {showThumbnails && slideCount > 0 && !isFullscreen && (
              <div className="border-r shrink-0 overflow-hidden">
                <PptxThumbnailStrip
                  content={content as ArrayBuffer}
                  slideCount={slideCount}
                  currentSlide={currentSlide}
                  onNavigate={setCurrentSlide}
                />
              </div>
            )}
            {/* Main slide area — fills remaining horizontal space */}
            <div
              ref={slideContainerRef}
              className={cn(
                'flex flex-col items-center flex-1 min-w-0',
                isFullscreen && 'bg-black h-screen w-screen justify-center'
              )}
            >
              <div className={cn('w-full', isFullscreen && 'max-w-5xl px-4')}>
                <PptxRenderer
                  content={content as ArrayBuffer}
                  currentSlide={currentSlide}
                  onSlideCountKnown={setSlideCount}
                  onNavigate={setCurrentSlide}
                />
              </div>
              {/* Navigation toolbar */}
              <div
                className={cn(
                  'flex items-center justify-center gap-2 py-2',
                  isFullscreen &&
                    'absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/60 rounded-lg px-4 py-2'
                )}
              >
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn('size-8', isFullscreen && 'text-white hover:bg-white/10')}
                  disabled={currentSlide === 0}
                  onClick={() => setCurrentSlide((s) => s - 1)}
                  aria-label="Previous slide"
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <span
                  className={cn(
                    'text-xs tabular-nums min-w-[80px] text-center',
                    isFullscreen ? 'text-white/80' : 'text-muted-foreground'
                  )}
                >
                  Slide {currentSlide + 1} of {slideCount || '…'}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn('size-8', isFullscreen && 'text-white hover:bg-white/10')}
                  disabled={slideCount === 0 || currentSlide >= slideCount - 1}
                  onClick={() => setCurrentSlide((s) => s + 1)}
                  aria-label="Next slide"
                >
                  <ChevronRight className="size-4" />
                </Button>
                {/* Exit fullscreen — visible only inside fullscreen since header is outside subtree */}
                {isFullscreen && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-white hover:bg-white/10 ml-2"
                    onClick={toggleFullscreen}
                    aria-label="Exit fullscreen"
                  >
                    <X className="size-4" />
                  </Button>
                )}
              </div>
            </div>
            {/* Annotation panel — right side; hidden in fullscreen for clean slide view */}
            {!isFullscreen && workspaceId && projectId && (
              <PptxAnnotationPanel
                workspaceId={workspaceId}
                projectId={projectId}
                artifactId={artifactId}
                currentSlide={currentSlide}
                currentUserId={currentUserId}
              />
            )}
          </div>
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

            {/* Thumbnail strip toggle — only shown for PPTX when slides are loaded */}
            {rendererType === 'pptx' && slideCount > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setShowThumbnails((s) => !s)}
                aria-label={showThumbnails ? 'Hide slide thumbnails' : 'Show slide thumbnails'}
                aria-pressed={showThumbnails}
              >
                <LayoutList className="size-4" />
              </Button>
            )}

            {/* Fullscreen slideshow button — only shown for PPTX when slides are loaded */}
            {rendererType === 'pptx' && slideCount > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={toggleFullscreen}
                aria-label={
                  isFullscreen ? 'Exit fullscreen slideshow' : 'Enter fullscreen slideshow'
                }
              >
                <Play className="size-4" />
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
});
