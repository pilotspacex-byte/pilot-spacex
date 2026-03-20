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

export function FigureNodeView({ node, editor }: NodeViewProps) {
  const { src, alt, status, artifactId } = node.attrs as {
    src: string | null;
    alt: string;
    artifactId: string | null;
    status: 'uploading' | 'ready' | 'error';
  };

  const isUploading = status === 'uploading';

  return (
    <NodeViewWrapper>
      <figure
        className="note-figure my-4 group"
        data-figure-artifact-id={artifactId ?? ''}
        onClick={() => {
          if (!artifactId || status !== 'ready') return;
          const imgMime = src?.match(/\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)/i)
            ? `image/${(src.match(/\.(\w+)$/)?.[1] ?? 'png').toLowerCase()}`
            : 'image/png';
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
        }}
      >
        {isUploading ? (
          <div className="flex items-center justify-center rounded-lg border border-border bg-muted/30 h-40 w-full">
            <div className="text-sm text-muted-foreground animate-pulse">Uploading image…</div>
          </div>
        ) : src ? (
          <img
            src={src}
            alt={alt}
            className="note-figure-img rounded-lg max-w-full h-auto block"
            draggable={false}
          />
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 h-40 w-full">
            <div className="text-sm text-destructive">Image failed to load</div>
          </div>
        )}
        {/* NodeViewContent as="div" — figcaption semantics via CSS role, not HTML tag,
            because NodeViewContent only accepts "div" in its prop types */}
        <NodeViewContent
          as="div"
          className="note-figure-caption mt-2 text-sm text-muted-foreground italic text-center empty:before:content-[attr(data-placeholder)] empty:before:text-muted-foreground/50"
          data-placeholder={editor.isEditable ? 'Add a caption…' : ''}
        />
      </figure>
    </NodeViewWrapper>
  );
}
