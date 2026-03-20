'use client';

/**
 * FigureView — intentionally minimal.
 *
 * Unlike FileCardView (which needs MobX ArtifactStore for upload progress),
 * FigureNodeView handles all rendering directly. The image src/status attrs
 * come from node.attrs in FigureNodeView, and the caption text is a TipTap
 * content slot rendered by NodeViewContent.
 *
 * This file exists to maintain the expected project structure (file-card/ and
 * figure/ parallel layout). It is not currently used by FigureNodeView.
 *
 * If Phase 34 (FilePreviewModal) needs to wire click-to-preview on figure nodes,
 * that can be added here as a click handler passed via a FigureContext.
 */
export {}; // No exports — FigureNodeView handles all rendering
