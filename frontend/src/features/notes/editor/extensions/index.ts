/**
 * TipTap Extensions Index
 * Barrel export for all editor extensions
 */

// Core extensions
export { BlockIdExtension, type BlockIdOptions } from './BlockIdExtension';
export {
  GhostTextExtension,
  ghostTextStyles,
  type GhostTextOptions,
  type GhostTextContext,
} from './GhostTextExtension';
export { AnnotationMark, type AnnotationMarkOptions } from './AnnotationMark';

// UI extensions
export {
  MarginAnnotationExtension,
  marginAnnotationStyles,
  type MarginAnnotationOptions,
  type BlockAnnotationData,
} from './MarginAnnotationExtension';
export {
  MarginAnnotationAutoTriggerExtension,
  type MarginAnnotationAutoTriggerOptions,
  type MarginAnnotationContext,
} from './MarginAnnotationAutoTriggerExtension';
export {
  IssueLinkExtension,
  issueLinkStyles,
  type IssueLinkOptions,
  type IssueLinkMatch,
  type IssuePreview,
} from './IssueLinkExtension';
export {
  CodeBlockExtension,
  codeBlockStyles,
  lowlight,
  SUPPORTED_LANGUAGES,
  type CodeBlockOptions,
} from './CodeBlockExtension';
export {
  MentionExtension,
  mentionStyles,
  type MentionOptions,
  type MentionUser,
} from './MentionExtension';
export {
  SlashCommandExtension,
  slashCommandStyles,
  type SlashCommandOptions,
  type SlashCommand,
} from './SlashCommandExtension';
export {
  InlineIssueExtension,
  type InlineIssueOptions,
  type InlineIssueAttributes,
  type IssueType,
  type IssueState,
  type IssuePriority,
} from './InlineIssueExtension';
export { InlineIssueComponent } from './InlineIssueComponent';
export { ParagraphSplitExtension, type ParagraphSplitOptions } from './ParagraphSplitExtension';

// Factory function
export { createEditorExtensions, type EditorExtensionsOptions } from './createEditorExtensions';
