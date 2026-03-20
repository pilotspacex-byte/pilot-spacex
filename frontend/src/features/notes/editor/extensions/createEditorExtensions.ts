/**
 * createEditorExtensions - Factory for TipTap editor configuration
 * Assembles all extensions for the Note canvas editor.
 *
 * ## Extension Loading Order
 *
 * Extension registration order matters in TipTap/ProseMirror because:
 * 1. ProseMirror plugins execute in registration order — later plugins see
 *    the document state after earlier plugins have run.
 * 2. Node/mark type resolution uses first-registered-wins for conflicting
 *    schemas (e.g., StarterKit's codeBlock is disabled so our custom
 *    CodeBlockExtension can take its place).
 * 3. Decorations from later plugins overlay earlier ones.
 *
 * ### Current order (grouped by responsibility):
 *
 * **Group 1 — Foundation** (must come first):
 *   StarterKit, Markdown, TaskList/TaskItem, Table/Row/Header/Cell
 *
 * **Group 2 — Editor UX**:
 *   Placeholder, CharacterCount
 *
 * **Group 3 — Block-type extensions** (custom node types):
 *   CodeBlockExtension
 *   >>> NEW PM BLOCK EXTENSIONS GO HERE (see PRE-002 below) <<<
 *
 * **Group 4 — Block IDs** (MUST remain after all block-type extensions):
 *   BlockIdExtension — assigns stable UUIDs to every block-level node.
 *   These IDs are used by AI tools for block references, annotation linking,
 *   scroll sync, and virtualization. It must run AFTER all block-type nodes
 *   are registered so it can traverse the complete schema and assign IDs
 *   to every block node, including any new PM block types.
 *
 * **Group 5 — Inline marks & decorations** (operate on existing blocks):
 *   GhostTextExtension, AnnotationMark, MarginAnnotation*,
 *   IssueLinkExtension, MentionExtension, SlashCommandExtension,
 *   InlineIssueExtension, ParagraphSplitExtension
 *
 * **Group 6 — Visual overlays** (read-only decorations, order-independent):
 *   AIBlockProcessingExtension, LineGutterExtension
 *
 * ### PRE-002: Adding new PM block extensions (013-pm-note-extensions)
 *
 * When adding new block-type extensions (e.g., Enhanced CodeBlock,
 * TaskItemEnhanced, PMBlockExtension/DiagramBlock), insert them in
 * **Group 3** — BEFORE BlockIdExtension and AFTER CodeBlockExtension.
 * This ensures BlockIdExtension sees all block node types when assigning
 * UUIDs. Failing to do so will cause new block types to lack stable IDs,
 * breaking AI block references and annotation linking.
 */
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { PullQuoteExtension } from './PullQuoteExtension';
import CharacterCount from '@tiptap/extension-character-count';
import TaskList from '@tiptap/extension-task-list';
import { TaskItemEnhanced } from './pm-blocks/TaskItemEnhanced';
import { ProgressBarDecoration } from './pm-blocks/ProgressBarDecoration';
import { PMBlockExtension } from './pm-blocks/PMBlockExtension';
import { FileCardExtension } from './file-card/FileCardExtension';
import { FigureExtension } from './figure/FigureExtension';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableHeader } from '@tiptap/extension-table-header';
import { TableCell } from '@tiptap/extension-table-cell';
import { Markdown } from 'tiptap-markdown';
import { Extension } from '@tiptap/core';
import type { AnyExtension, Editor } from '@tiptap/core';

import { BlockIdExtension, type BlockIdOptions } from './BlockIdExtension';
import {
  GhostTextExtension,
  type GhostTextOptions,
  type GhostTextContext,
} from './GhostTextExtension';
import { AnnotationMark, type AnnotationMarkOptions } from './AnnotationMark';
import {
  MarginAnnotationExtension,
  type MarginAnnotationOptions,
  type BlockAnnotationData,
} from './MarginAnnotationExtension';
import {
  MarginAnnotationAutoTriggerExtension,
  type MarginAnnotationAutoTriggerOptions,
  type MarginAnnotationContext,
} from './MarginAnnotationAutoTriggerExtension';
import { IssueLinkExtension, type IssueLinkOptions, type IssuePreview } from './IssueLinkExtension';
import {
  EntityHighlightExtension,
  type EntityHighlightOptions,
  type EntityMatch,
} from './EntityHighlightExtension';
import { CodeBlockExtension, type CodeBlockOptions } from './CodeBlockExtension';
import { MentionExtension, type MentionOptions, type MentionUser } from './MentionExtension';
import {
  SlashCommandExtension,
  type SlashCommandOptions,
  type SlashCommand,
} from './SlashCommandExtension';
import {
  InlineIssueExtension,
  type InlineIssueOptions,
  type InlineIssueAttributes,
} from './InlineIssueExtension';
import { ParagraphSplitExtension, type ParagraphSplitOptions } from './ParagraphSplitExtension';
import {
  NoteLinkExtension,
  type NoteLinkOptions,
  type NoteLinkSearchResult,
} from './NoteLinkExtension';
import { AIBlockProcessingExtension } from './AIBlockProcessingExtension';
import { OwnershipExtension, type OwnershipOptions, type BlockOwner } from './OwnershipExtension';
import { DensityExtension, type DensityOptions } from './DensityExtension';
import Highlight from '@tiptap/extension-highlight';
import { YoutubeExtension } from './YoutubeExtension';
import { VimeoNode } from './VimeoNode';
import { VideoPasteDetector } from './VideoPasteDetector';

export interface EditorExtensionsOptions {
  /** Placeholder text for empty editor */
  placeholder?: string;
  /** Character limit for the editor */
  characterLimit?: number;
  /** Ghost text configuration */
  ghostText?: Partial<GhostTextOptions> & {
    onTrigger?: (context: GhostTextContext) => void;
    onAccept?: (text: string, acceptType: 'full' | 'word') => void;
    onDismiss?: () => void;
  };
  /** Block ID configuration */
  blockId?: Partial<BlockIdOptions>;
  /** Annotation configuration */
  annotation?: Partial<AnnotationMarkOptions>;
  /** Margin annotation configuration */
  marginAnnotation?: Partial<MarginAnnotationOptions> & {
    annotations?: Map<string, BlockAnnotationData>;
    onClick?: (blockId: string) => void;
  };
  /** Margin annotation auto-trigger configuration */
  marginAnnotationAutoTrigger?: Partial<MarginAnnotationAutoTriggerOptions> & {
    onTrigger?: (context: MarginAnnotationContext) => void;
  };
  /** Issue link configuration */
  issueLink?: Partial<IssueLinkOptions> & {
    onHover?: (issueId: string) => Promise<IssuePreview | null>;
    onClick?: (issueId: string) => void;
  };
  /** Code block configuration */
  codeBlock?: Partial<CodeBlockOptions>;
  /** Enable code block syntax highlighting (default: true) */
  codeHighlighting?: boolean;
  /** Enable mentions (default: false) */
  enableMentions?: boolean;
  /** Mention configuration */
  mention?: Partial<MentionOptions> & {
    onSearch?: (query: string) => Promise<MentionUser[]>;
    onSelect?: (user: MentionUser) => void;
  };
  /** Enable slash commands (default: true) */
  enableSlashCommands?: boolean;
  /** Slash command configuration */
  slashCommand?: Partial<SlashCommandOptions> & {
    commands?: SlashCommand[];
    onExecute?: (command: SlashCommand) => void;
    onAICommand?: (command: string, editor: Editor) => Promise<void>;
  };
  /** Enable inline issues (default: true) */
  enableInlineIssues?: boolean;
  /** Inline issue configuration */
  inlineIssue?: Partial<InlineIssueOptions> & {
    onClick?: (issueId: string) => void;
    onHover?: (issueId: string) => Promise<InlineIssueAttributes | null>;
    onUnlink?: (issueId: string) => void;
  };
  /** Enable paragraph split on double newlines (default: true) */
  enableParagraphSplit?: boolean;
  /** Paragraph split configuration */
  paragraphSplit?: Partial<ParagraphSplitOptions>;
  /** Enable note-to-note linking with [[ trigger (default: false) */
  enableNoteLinks?: boolean;
  /** Note link configuration */
  noteLink?: Partial<NoteLinkOptions> & {
    onSearch?: (query: string) => Promise<NoteLinkSearchResult[]>;
    onLinkCreated?: (targetNoteId: string, blockId?: string) => void;
    onClick?: (noteId: string) => void;
  };
  /** Ownership extension configuration (M6b — Feature 016) */
  ownership?: Partial<OwnershipOptions> & {
    /** Called when human tries to edit an AI block (show edit guard toast) */
    onGuardBlock?: (blockId: string, owner: BlockOwner) => void;
  };
  /** Density extension configuration (M8 — Feature 016 Sprint 3) */
  density?: Partial<DensityOptions>;
  /**
   * Entity highlight configuration (project name detection).
   * H-6: Do NOT pass projectEntities here — inject via extensionStorage useEffect
   * in NoteCanvasEditor to avoid triggering a full editor remount.
   */
  entityHighlight?: Omit<Partial<EntityHighlightOptions>, 'projectEntities'> & {
    onEntityHover?: (entity: EntityMatch) => void;
    onEntityClick?: (entity: EntityMatch) => void;
  };
}

/**
 * Creates a configured set of TipTap extensions for the Note editor
 *
 * Includes:
 * - StarterKit (basic formatting, lists, headings, etc.)
 * - Placeholder text
 * - Character count
 * - Code block with syntax highlighting
 * - Block IDs for annotation linking
 * - Ghost text for AI suggestions
 * - Annotation marks for highlighting
 * - Margin annotations for sidebar indicators
 * - Issue link auto-detection
 * - Optional mentions
 * - Slash commands for quick actions
 *
 * @example
 * ```tsx
 * const extensions = createEditorExtensions({
 *   placeholder: 'Start writing...',
 *   ghostText: {
 *     onTrigger: (context) => {
 *       // Trigger AI suggestion
 *     },
 *   },
 *   issueLink: {
 *     onClick: (issueId) => {
 *       // Open issue panel
 *     },
 *   },
 *   enableSlashCommands: true,
 *   slashCommand: {
 *     onAICommand: async (command, editor) => {
 *       // Handle AI command
 *     },
 *   },
 * });
 *
 * const editor = new Editor({ extensions });
 * ```
 */
export function createEditorExtensions(options: EditorExtensionsOptions = {}): AnyExtension[] {
  const {
    placeholder = 'Start typing, or press / for commands...',
    characterLimit = 100000,
    ghostText,
    blockId,
    annotation,
    marginAnnotation,
    marginAnnotationAutoTrigger,
    issueLink,
    codeBlock,
    codeHighlighting = true,
    enableMentions = false,
    mention,
    enableSlashCommands = true,
    slashCommand,
    enableInlineIssues = true,
    inlineIssue,
    enableParagraphSplit = true,
    paragraphSplit,
    enableNoteLinks = false,
    noteLink,
    ownership,
    density,
    entityHighlight,
  } = options;

  const extensions: AnyExtension[] = [];

  // ── Group 1: Foundation ────────────────────────────────────────────
  // Base StarterKit (excludes code block since we're using custom version)
  extensions.push(
    StarterKit.configure({
      codeBlock: false,
      blockquote: false, // Disabled — replaced by PullQuoteExtension below (EDIT-01)
      heading: {
        levels: [1, 2, 3],
      },
      bulletList: {
        keepMarks: true,
        keepAttributes: false,
      },
      orderedList: {
        keepMarks: true,
        keepAttributes: false,
      },
    })
  );

  // PullQuoteExtension replaces StarterKit's blockquote (blockquote: false above).
  // Stays in Group 1 (same schema role as blockquote). Name 'blockquote' kept so
  // BlockIdExtension covers it automatically. See PRE-002 comment for Group 3 rules.
  extensions.push(PullQuoteExtension);

  // Markdown extension for bidirectional markdown support
  extensions.push(
    Markdown.configure({
      html: true, // Allow HTML in markdown (for block ID comments)
      tightLists: true,
      breaks: false,
      linkify: false,
      transformPastedText: false,
      transformCopiedText: false,
    })
  );

  // Task list for issue extraction (checkboxes)
  extensions.push(
    TaskList.configure({
      HTMLAttributes: {
        class: 'task-list',
      },
    })
  );

  // TaskItemEnhanced replaces default TaskItem — adds assignee, dueDate,
  // priority, isOptional, estimatedEffort, conditionalParentId attrs (FR-013 to FR-018)
  extensions.push(
    TaskItemEnhanced.configure({
      nested: true,
      HTMLAttributes: {
        class: 'task-item',
      },
    })
  );

  // Table support (for markdown tables from AI content)
  extensions.push(
    Table.configure({
      resizable: false,
      HTMLAttributes: {
        class: 'note-table',
      },
    })
  );
  extensions.push(TableRow);
  extensions.push(TableHeader);
  extensions.push(TableCell);

  // ── Group 2: Editor UX ──────────────────────────────────────────────
  // Placeholder
  extensions.push(
    Placeholder.configure({
      placeholder: ({ node }) => {
        if (node.type.name === 'heading') {
          const level = node.attrs.level as number;
          return `Heading ${level}`;
        }
        return placeholder;
      },
      emptyEditorClass: 'is-editor-empty',
      emptyNodeClass: 'is-node-empty',
      showOnlyWhenEditable: true,
      showOnlyCurrent: true,
    })
  );

  // Character count
  extensions.push(
    CharacterCount.configure({
      limit: characterLimit,
      mode: 'textSize',
    })
  );

  // ── Group 3: Block-type extensions ──────────────────────────────────
  // New PM block extensions (PRE-002) should be added at the end of this
  // group, AFTER CodeBlockExtension and BEFORE the Group 4 marker below.
  // Code block with syntax highlighting
  if (codeHighlighting) {
    extensions.push(
      CodeBlockExtension.configure({
        defaultLanguage: 'plaintext',
        lineNumbers: false,
        showCopyButton: true,
        ...codeBlock,
      })
    );
  }

  // ProgressBarDecoration — renders progress bar above TaskList nodes (FR-019)
  extensions.push(
    Extension.create({
      name: 'progressBarDecoration',
      addProseMirrorPlugins() {
        return [ProgressBarDecoration];
      },
    })
  );

  // PMBlockExtension — generic PM block node (decision, form, raci, risk, timeline, dashboard)
  extensions.push(PMBlockExtension);
  extensions.push(FileCardExtension); // Group 3 — ARTF-01, ARTF-02, ARTF-03
  extensions.push(FigureExtension); // Group 3 — EDIT-04, EDIT-05
  // YoutubeExtension — inline YouTube iframe player (VID-01, VID-04)
  // MUST be in Group 3 before BlockIdExtension (PRE-002)
  extensions.push(YoutubeExtension);
  // VimeoNode — inline Vimeo iframe player (VID-02, VID-04)
  // MUST be in Group 3 before BlockIdExtension (PRE-002)
  extensions.push(VimeoNode);

  // ── Group 4: Block IDs (MUST be after all block-type extensions) ────
  // BlockIdExtension assigns stable UUIDs to every block-level node.
  // It MUST remain after Group 3 so it sees all registered block types.
  // See PRE-002 in specs/013-pm-note-extensions/spec.md.
  extensions.push(
    BlockIdExtension.configure({
      ...blockId,
    })
  );

  // ── Group 5: Inline marks & decorations ─────────────────────────────
  // These operate on existing block nodes; order within this group is flexible.
  // Ghost text for AI suggestions
  extensions.push(
    GhostTextExtension.configure({
      debounceMs: 500,
      minChars: 10,
      enabled: true,
      ...ghostText,
    })
  );

  // Annotation marks
  extensions.push(
    AnnotationMark.configure({
      ...annotation,
    })
  );

  // Text highlight (yellow background mark — used by SelectionToolbar)
  extensions.push(Highlight.configure({ multicolor: false }));

  // Margin annotation indicators
  extensions.push(
    MarginAnnotationExtension.configure({
      annotations: new Map(),
      ...marginAnnotation,
    })
  );

  // Margin annotation auto-trigger
  extensions.push(
    MarginAnnotationAutoTriggerExtension.configure({
      debounceMs: 2000,
      minChars: 50,
      contextBlocks: 3,
      enabled: true,
      ...marginAnnotationAutoTrigger,
    })
  );

  // Issue link auto-detection
  extensions.push(
    IssueLinkExtension.configure({
      ...issueLink,
    })
  );

  // Entity highlight (project name detection) — after IssueLinkExtension (lower priority).
  // H-6: Always register with empty initial entities; actual list is injected via
  // editor.extensionStorage['entityHighlight'].entities in NoteCanvasEditor useEffect.
  extensions.push(
    EntityHighlightExtension.configure({
      ...entityHighlight,
    })
  );

  // Mentions (optional)
  if (enableMentions && mention?.onSearch) {
    extensions.push(
      MentionExtension.configure({
        trigger: '@',
        maxSuggestions: 10,
        debounceMs: 150,
        ...mention,
      })
    );
  }

  // Slash commands
  if (enableSlashCommands) {
    extensions.push(
      SlashCommandExtension.configure({
        maxSuggestions: 10,
        ...slashCommand,
      })
    );
  }

  // Video paste detection (VID-03) — offers embed prompt on standalone YouTube/Vimeo URL paste
  extensions.push(VideoPasteDetector);

  // Inline issue references (per UI Spec v3.3 / DD-013)
  if (enableInlineIssues) {
    extensions.push(
      InlineIssueExtension.configure({
        onIssueClick: inlineIssue?.onClick,
        onIssueHover: inlineIssue?.onHover,
        onIssueUnlink: inlineIssue?.onUnlink,
        ...inlineIssue,
      })
    );
  }

  // Note-to-note linking with [[ trigger (018-note-editor-enhancements)
  if (enableNoteLinks && noteLink?.onSearch) {
    extensions.push(
      NoteLinkExtension.configure({
        maxSuggestions: 10,
        debounceMs: 150,
        ...noteLink,
      })
    );
  }

  // Paragraph split on double newlines (visual block separation)
  if (enableParagraphSplit) {
    extensions.push(
      ParagraphSplitExtension.configure({
        convertDoubleHardBreak: true,
        transformPaste: true,
        normalizeOnLoad: true,
        ...paragraphSplit,
      })
    );
  }

  // ── Group 6: Visual overlays (read-only, order-independent) ─────────
  // Ownership extension — block-level human/AI boundary enforcement (M6b, Feature 016)
  extensions.push(
    OwnershipExtension.configure({
      actor: 'human',
      ...ownership,
    })
  );

  // AI block processing indicator (decoration-based, reads from editor.storage)
  extensions.push(
    AIBlockProcessingExtension.configure({
      attributeName: 'blockId',
    })
  );

  // Density extension — collapse/focus mode for AI blocks (M8, Feature 016 Sprint 3)
  extensions.push(
    DensityExtension.configure({
      noteId: '',
      focusModeDefault: false,
      ...density,
    })
  );

  // // Line gutter: line numbers (CSS counter) + heading fold/unfold widgets
  // extensions.push(
  //   LineGutterExtension.configure({
  //     foldableTypes: ['heading'],
  //   })
  // );

  return extensions;
}

export type { AnyExtension };
