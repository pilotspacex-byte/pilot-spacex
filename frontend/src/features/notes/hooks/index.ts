/**
 * Notes Hooks - Barrel Export
 */

// Tree hooks
export { useProjectPageTree, projectTreeKeys } from './useProjectPageTree';
export { usePersonalPages, personalPagesKeys } from './usePersonalPages';

// Query hooks
export { useNotes, useInfiniteNotes, notesKeys, NOTES_QUERY_KEY } from './useNotes';
export type { UseNotesOptions } from './useNotes';

export { useNote, useNoteAnnotations } from './useNote';
export type { UseNoteOptions } from './useNote';

// Mutation hooks
export { useMovePage } from './useMovePage';
export { useReorderPage } from './useReorderPage';
export { useCreateNote, createNoteDefaults } from './useCreateNote';
export type { UseCreateNoteOptions } from './useCreateNote';

export { useUpdateNote, useUpdateNoteContent } from './useUpdateNote';
export type { UseUpdateNoteOptions, UpdateNoteData } from './useUpdateNote';

export { useDeleteNote } from './useDeleteNote';
export type { UseDeleteNoteOptions } from './useDeleteNote';

// Auto-save
export { useAutoSave, getStatusIndicator } from './useAutoSave';
export type { UseAutoSaveOptions, UseAutoSaveReturn, AutoSaveStatus } from './useAutoSave';

// Real-time
export { useIssueSyncListener, getSyncIndicatorConfig } from './useIssueSyncListener';
export type {
  UseIssueSyncListenerOptions,
  UseIssueSyncListenerReturn,
  IssueSyncEvent,
} from './useIssueSyncListener';

// Issue extraction
export { useIssueExtraction } from './useIssueExtraction';
