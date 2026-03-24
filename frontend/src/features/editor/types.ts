export type FileSource = 'artifact' | 'local' | 'note' | 'remote';
export type EditorMode = 'edit' | 'preview';
export type PMBlockType =
  | 'decision'
  | 'raci'
  | 'risk'
  | 'dependency'
  | 'timeline'
  | 'sprint-board'
  | 'dashboard'
  | 'form'
  | 'release-notes'
  | 'capacity-plan';

/** PM block type extended with plugin-registered types (any string). */
export type ExtendedPMBlockType = PMBlockType | (string & {});

export interface OpenFile {
  id: string;
  name: string;
  path: string;
  source: FileSource;
  language: string;
  content: string;
  isDirty: boolean;
  isReadOnly: boolean;
}

export interface PMBlockMarker {
  type: ExtendedPMBlockType;
  startLine: number; // 1-based line of opening ```pm:type
  endLine: number; // 1-based line of closing ```
  data: Record<string, unknown> | null; // Parsed JSON or null if malformed
  raw: string; // Raw JSON string between markers
}

export interface GhostTextContext {
  textBeforeCursor: string;
  textAfterCursor: string;
  cursorPosition: number;
  noteId: string;
}
