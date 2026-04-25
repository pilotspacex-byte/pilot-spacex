import type { User, UserBrief } from './workspace';
import type { LinkedIssueBrief } from './issue';

/**
 * TipTap/ProseMirror JSON content structure
 */
export interface JSONContent {
  type?: string;
  attrs?: Record<string, unknown>;
  content?: JSONContent[];
  marks?: { type: string; attrs?: Record<string, unknown> }[];
  text?: string;
}

/**
 * Note entity - primary document for Note-First workflow
 */
export interface Note {
  id: string;
  title: string;
  content?: JSONContent;
  summary?: string;
  wordCount: number;
  readingTimeMins?: number;
  isPinned: boolean;
  /** Whether note contains AI-assisted edits (per UI Spec v3.3) */
  isAIAssisted?: boolean;
  projectId?: string;
  templateId?: string;
  ownerId?: string;
  lastEditedById?: string;
  workspaceId: string;
  /** Parent note ID for tree nesting (null = root note) */
  parentId?: string | null;
  /** Tree depth: 0=root, 1=section, 2=page */
  depth?: number;
  /** Sibling ordering position within parent group */
  position?: number;
  /** Optional emoji icon for page visual identity */
  iconEmoji?: string | null;
  /**
   * Topic tree parent (Phase 93). camelCase alias of backend `parent_topic_id`.
   * `null` indicates a root topic. Always emitted by the backend (NoteResponse 93-02).
   */
  parentTopicId?: string | null;
  /**
   * Topic tree depth (Phase 93). camelCase alias of backend `topic_depth`.
   * Root topics are depth 0; max enforced at 5 by the backend service.
   */
  topicDepth?: number;
  owner?: User;
  collaborators?: User[];
  linkedIssues: LinkedIssueBrief[];
  annotations?: NoteAnnotation[];
  topics?: string[];
  createdAt: string;
  updatedAt: string;
}

/**
 * @deprecated Use JSONContent instead
 */
export interface NoteContent {
  type: 'doc';
  content: NoteBlock[];
}

/**
 * @deprecated Use JSONContent instead
 */
export interface NoteBlock {
  id: string;
  type: string;
  content?: unknown;
  attrs?: Record<string, unknown>;
}

/**
 * Annotation type for AI-generated suggestions
 */
export type AnnotationType =
  | 'suggestion'
  | 'warning'
  | 'issue_candidate'
  | 'info'
  | 'question'
  | 'insight'
  | 'reference';

/**
 * Annotation status for tracking user actions
 */
export type AnnotationStatus = 'pending' | 'accepted' | 'rejected' | 'dismissed';

/**
 * AI annotation metadata
 */
export interface AnnotationMetadata {
  title?: string;
  summary?: string;
  suggestedText?: string;
  references?: Array<{ title: string; url: string }>;
}

/**
 * AI annotation on a note block
 */
export interface NoteAnnotation {
  id: string;
  noteId: string;
  blockId: string;
  content: string;
  type: AnnotationType;
  confidence: number;
  status: AnnotationStatus;
  aiMetadata?: AnnotationMetadata;
  createdAt: string;
  updatedAt?: string;
  /** @deprecated Use status instead */
  resolved?: boolean;
}

export interface CreateNoteData {
  title: string;
  content?: JSONContent;
  workspaceId: string;
  projectId?: string;
  templateId?: string;
  /** Parent note ID for tree nesting */
  parentId?: string;
}

export interface UpdateNoteData {
  title?: string;
  content?: JSONContent;
  projectId?: string;
  isPinned?: boolean;
  iconEmoji?: string | null;
}

// Note-to-Note Link Types
export interface NoteNoteLink {
  id: string;
  sourceNoteId: string;
  targetNoteId: string;
  linkType: 'inline' | 'embed';
  blockId?: string;
  workspaceId: string;
  targetNoteTitle?: string;
}

export interface NoteBacklink {
  id: string;
  sourceNoteId: string;
  targetNoteId: string;
  linkType: 'inline' | 'embed';
  blockId?: string;
  workspaceId: string;
  sourceNoteTitle?: string;
}

export interface NoteLinkSearchResult {
  id: string;
  title: string;
  updatedAt: string;
}

export type { User, UserBrief, LinkedIssueBrief };
