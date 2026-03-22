'use client';

/**
 * FigureNodeView — Plain (non-observer) NodeView wrapper for FigureExtension.
 *
 * IMPORTANT: Do NOT wrap in observer(). Same constraint as FileCardNodeView.
 * See: frontend/src/features/issues/components/issue-editor-content.tsx
 * Reason: TipTap ReactNodeViewRenderer + MobX observer() causes nested flushSync
 * in React 19 (useSyncExternalStore + ReactNodeViewRenderer conflict).
 *
 * The figure has content: 'inline*' so figcaption text is rendered by
 * TipTap's NodeViewContent component, not by this wrapper.
 */
import { NodeViewWrapper, NodeViewContent, type NodeViewProps } from '@tiptap/react';
import { ZoomIn } from 'lucide-react';

export function FigureNodeView({ node, editor }: NodeViewProps) {
  const { src, alt, status, artifactId } = node.attrs as {
    src: string | null;
    alt: string;
    artifactId: string | null;
    status: 'uploading' | 'ready' | 'error';
  };

  const isUploading = status === 'uploading';
  const isReady = status === 'ready' && src;
  const hasCaption = node.textContent.length > 0;

  function handlePreview() {
    if (!artifactId || status !== 'ready') return;
    const extMatch = src ? /\.(\w+)(?:[?#]|$)/i.exec(src) : null;
    const extKey = extMatch?.[1]?.toLowerCase() ?? 'png';
    const mimeMap: Record<string, string> = {
      png: 'image/png',
      jpg: 'image/jpeg',
      jpeg: 'image/jpeg',
      gif: 'image/gif',
      webp: 'image/webp',
      svg: 'image/svg+xml',
      bmp: 'image/bmp',
      ico: 'image/x-icon',
    };
    const imgMime = mimeMap[extKey] ?? 'image/png';
    window.dispatchEvent(
      new CustomEvent('pilot:preview-artifact', {
        detail: {
          artifactId,
          filename: alt || 'image',
          mimeType: imgMime,
          signedUrl: src,
        },
      })
    );
  }

  return (
    <NodeViewWrapper>
      <figure className="note-figure my-4 group" data-figure-artifact-id={artifactId ?? ''}>
        {isUploading ? (
          <div className="flex items-center justify-center rounded-lg border border-border bg-muted/30 h-40 w-full">
            <div className="text-sm text-muted-foreground animate-pulse">Uploading image…</div>
          </div>
        ) : isReady ? (
          <div
            className="relative cursor-pointer rounded-lg overflow-hidden"
            role="button"
            tabIndex={0}
            aria-label={`View ${alt || 'image'} full size`}
            onClick={handlePreview}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handlePreview();
              }
            }}
          >
            <img
              src={src}
              alt={alt}
              className="note-figure-img rounded-lg max-w-full h-auto block transition-[filter] duration-200 group-hover:brightness-[0.92]"
              draggable={false}
            />
            {/* Hover overlay with zoom icon */}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
              <div className="flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs text-white/90 backdrop-blur-sm">
                <ZoomIn className="size-3.5" />
                Click to preview
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 h-40 w-full">
            <div className="text-sm text-destructive">Image failed to load</div>
          </div>
        )}
        {/* Caption area with centered placeholder */}
        <div className="relative mt-2">
          {editor.isEditable && !hasCaption && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
              <span className="text-sm italic text-muted-foreground/50">Add a caption…</span>
            </div>
          )}
          <NodeViewContent
            as="div"
            className="note-figure-caption text-sm text-muted-foreground italic text-center min-h-[1.5em]"
          />
        </div>
      </figure>
    </NodeViewWrapper>
  );
}
