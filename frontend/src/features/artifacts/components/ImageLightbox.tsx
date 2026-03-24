'use client';

import * as React from 'react';
import { Download, X, ZoomIn, ZoomOut } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Image Lightbox -- gallery-style fullscreen overlay for images
// ---------------------------------------------------------------------------
export function ImageLightbox({
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
      {/* Backdrop -- click to close */}
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
