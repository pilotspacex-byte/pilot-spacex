'use client';

/**
 * NoteCanvas - Thin wrapper for backward compatibility.
 *
 * The implementation has been split into:
 * - NoteCanvasEditor.tsx: Editor initialization, TipTap hooks, extension config, event handlers
 * - NoteCanvasLayout.tsx: Responsive layout rendering (desktop/mobile), header, toolbar, ChatView
 *
 * This file re-exports both the component and all public types/utilities so existing
 * imports from './NoteCanvas' continue to work without changes.
 */
export { extractFirstHeadingText } from './NoteCanvasEditor';
export type { NoteCanvasProps } from './NoteCanvasEditor';
export { NoteCanvasLayout as NoteCanvas } from './NoteCanvasLayout';
export { NoteCanvasLayout as default } from './NoteCanvasLayout';
