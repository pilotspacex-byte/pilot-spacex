/**
 * createEditorExtensions - Factory for TipTap editor configuration
 * Assembles all extensions for the Note canvas editor
 */
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
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
  } = options;

  const extensions: AnyExtension[] = [];

  // Base StarterKit (excludes code block since we're using custom version)
  extensions.push(
    StarterKit.configure({
      codeBlock: false,
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

  // Block IDs for annotation linking
  extensions.push(
    BlockIdExtension.configure({
      ...blockId,
    })
  );

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

  return extensions;
}

export type { AnyExtension };
