import type { Editor, JSONContent as TipTapJSONContent } from '@tiptap/core';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { EditorView } from '@tiptap/pm/view';
import type { Transaction } from '@tiptap/pm/state';
import type { AnnotationType } from '@/types';

/**
 * Re-export JSONContent from TipTap for consistency
 */
export type { TipTapJSONContent as JSONContent };

/**
 * Editor creation options
 */
export interface EditorOptions {
  content?: TipTapJSONContent;
  placeholder?: string;
  editable?: boolean;
  autofocus?: boolean | 'start' | 'end' | 'all' | number;
  /** Workspace ID — required for artifact upload in drop handler and slash commands */
  workspaceId?: string;
  /** Project ID — required for artifact upload in drop handler and slash commands */
  projectId?: string;
  onUpdate?: (props: { editor: Editor; transaction: Transaction }) => void;
  onSelectionUpdate?: (props: { editor: Editor; transaction: Transaction }) => void;
  onBlur?: (props: { editor: Editor; event: FocusEvent }) => void;
  onFocus?: (props: { editor: Editor; event: FocusEvent }) => void;
  onCreate?: (props: { editor: Editor }) => void;
  onDestroy?: () => void;
}

/**
 * Ghost text context for AI suggestion triggers
 */
export interface GhostTextContext {
  /** Current document text up to cursor */
  textBeforeCursor: string;
  /** Text after cursor in current block */
  textAfterCursor: string;
  /** Current cursor position in document */
  cursorPosition: number;
  /** ID of the current block */
  blockId: string;
  /** Type of the current block (paragraph, heading, etc.) */
  blockType: string;
  /** Full document content */
  document: TipTapJSONContent;
}

/**
 * Ghost text suggestion from AI
 */
export interface GhostTextSuggestion {
  /** The suggested text to display */
  text: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Unique ID for tracking */
  id: string;
}

/**
 * Ghost text extension options
 */
export interface GhostTextOptions {
  /** Debounce time in ms before triggering AI (default: 500) */
  debounceMs: number;
  /** Callback when ghost text should be triggered */
  onTrigger: (context: GhostTextContext) => void;
  /** Callback when ghost text is accepted */
  onAccept: (text: string, acceptType: 'full' | 'word') => void;
  /** Callback when ghost text is dismissed */
  onDismiss: () => void;
  /** Minimum characters before triggering */
  minChars: number;
  /** Whether to enable ghost text */
  enabled: boolean;
}

/**
 * Margin annotation display data
 */
export interface MarginAnnotationData {
  blockId: string;
  count: number;
  types: AnnotationType[];
  topOffset: number;
}

/**
 * Margin annotation extension options
 */
export interface MarginAnnotationOptions {
  /** Annotations to display */
  annotations: Map<string, { type: AnnotationType; count: number }[]>;
  /** Callback when annotation indicator is clicked */
  onClick: (blockId: string) => void;
}

/**
 * Issue link match data
 */
export interface IssueLinkMatch {
  /** Full match text (e.g., "PROJ-123") */
  text: string;
  /** Project identifier */
  project: string;
  /** Issue number */
  number: number;
  /** Start position in document */
  from: number;
  /** End position in document */
  to: number;
}

/**
 * Issue link extension options
 */
export interface IssueLinkOptions {
  /** Pattern for issue identifiers (default: /[A-Z]+-\d+/) */
  pattern: RegExp;
  /** Callback to fetch issue preview */
  onHover: (issueId: string) => Promise<IssuePreview | null>;
  /** Callback when issue link is clicked */
  onClick: (issueId: string) => void;
}

/**
 * Issue preview data for hover
 */
export interface IssuePreview {
  id: string;
  identifier: string;
  title: string;
  state: string;
  priority: string;
  assignee?: {
    name: string;
    avatarUrl?: string;
  };
}

/**
 * Mention suggestion data
 */
export interface MentionSuggestion {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

/**
 * Mention extension options
 */
export interface MentionOptions {
  /** Trigger character (default: '@') */
  trigger: string;
  /** Callback to search for users */
  onSearch: (query: string) => Promise<MentionSuggestion[]>;
  /** Callback when mention is inserted */
  onSelect: (user: MentionSuggestion) => void;
}

/**
 * Slash command definition
 */
export interface SlashCommand {
  /** Command name (e.g., 'heading') */
  name: string;
  /** Display label */
  label: string;
  /** Description for menu */
  description: string;
  /** Icon name from lucide */
  icon: string;
  /** Command group (formatting, blocks, ai, media) */
  group: 'formatting' | 'blocks' | 'ai' | 'media';
  /** Keyboard shortcut hint */
  shortcut?: string;
  /** Execute the command */
  execute: (editor: Editor) => void;
}

/**
 * Slash command extension options
 */
export interface SlashCommandOptions {
  /** Custom commands to add */
  commands: SlashCommand[];
  /** Callback when command is executed */
  onExecute: (command: SlashCommand) => void;
}

/**
 * Code block extension options
 */
export interface CodeBlockOptions {
  /** Default language */
  defaultLanguage: string;
  /** Available languages */
  languages: string[];
  /** Show line numbers */
  lineNumbers: boolean;
  /** Show copy button */
  showCopyButton: boolean;
}

/**
 * Block node with ID for annotation tracking
 */
export interface BlockNode {
  id: string;
  type: string;
  node: ProseMirrorNode;
  pos: number;
  dom?: HTMLElement;
}

/**
 * Editor context for extensions
 */
export interface EditorContext {
  editor: Editor;
  view: EditorView;
  getBlockById: (blockId: string) => BlockNode | null;
  getAllBlocks: () => BlockNode[];
}

/**
 * SSE connection state
 */
export type SSEConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

/**
 * Ghost text SSE event types
 */
export interface GhostTextSSEEvent {
  type: 'start' | 'chunk' | 'complete' | 'error';
  text?: string;
  error?: string;
  requestId: string;
}
