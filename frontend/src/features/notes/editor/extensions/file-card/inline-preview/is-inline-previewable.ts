/**
 * is-inline-previewable.ts
 *
 * Utility for determining whether a file can be previewed inline within a TipTap note.
 * Inline preview supports: code, markdown, csv, and json renderer types.
 *
 * All other types (image, download, html-preview, xlsx, docx, pptx, text) fall back
 * to the compact FileCard click-to-modal behavior.
 */

import { resolveRenderer } from '@/features/artifacts/utils/mime-type-router';

/** Renderer types supported for inline preview within a note card. */
export type InlineRendererType = 'code' | 'markdown' | 'csv' | 'json';

/** The set of renderer types that support inline preview. */
const INLINE_RENDERER_TYPES = new Set<string>(['code', 'markdown', 'csv', 'json']);

/**
 * Returns true if the given file's MIME type and filename map to a renderer type
 * that supports inline content preview (code, markdown, csv, json).
 *
 * @param mimeType - The file's MIME type (e.g. "text/plain", "application/json")
 * @param filename - The file's name (used for extension-based routing)
 */
export function isInlinePreviewable(mimeType: string, filename: string): boolean {
  const rendererType = resolveRenderer(mimeType, filename);
  return INLINE_RENDERER_TYPES.has(rendererType);
}

/**
 * Returns the inline renderer type for the file, or null if inline preview is not supported.
 *
 * @param mimeType - The file's MIME type
 * @param filename - The file's name
 */
export function getInlineRendererType(mimeType: string, filename: string): InlineRendererType | null {
  const rendererType = resolveRenderer(mimeType, filename);
  if (INLINE_RENDERER_TYPES.has(rendererType)) {
    return rendererType as InlineRendererType;
  }
  return null;
}
