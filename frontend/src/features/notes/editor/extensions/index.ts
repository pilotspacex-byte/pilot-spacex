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

// Ownership extension (M6b — Feature 016)
export {
  OwnershipExtension,
  getBlockOwner,
  canEdit,
  extractSkillName,
  buildAriaLabel,
  type BlockOwner,
  type EditActor,
  type OwnershipOptions,
  type OwnershipStorage,
} from './OwnershipExtension';

// Density extension (M8 — Feature 016 Sprint 3)
export {
  DensityExtension,
  buildCollapseSummary,
  type DensityOptions,
  type DensityStorage,
} from './DensityExtension';
export { DENSITY_STYLES } from './density-styles';

// Factory function
export { createEditorExtensions, type EditorExtensionsOptions } from './createEditorExtensions';
