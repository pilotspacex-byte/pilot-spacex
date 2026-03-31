/**
 * Barrel export for the inline-preview subdirectory.
 *
 * Consumers should import from this index rather than individual files
 * to maintain a stable public API boundary for Plan 02 wiring.
 */

export {
  isInlinePreviewable,
  getInlineRendererType,
  type InlineRendererType,
} from './is-inline-previewable';

export {
  FilePreviewConfigContext,
  useFilePreviewConfig,
  useFilePreviewConfigSafe,
  type FilePreviewConfig,
} from './FilePreviewConfigContext';

export {
  useInlinePreviewContent,
  type UseInlinePreviewContentResult,
} from './useInlinePreviewContent';

export { InlinePreviewHeader, type InlinePreviewHeaderProps } from './InlinePreviewHeader';

export { SkeletonPreviewCard } from './SkeletonPreviewCard';

export {
  InlineContentRenderer,
  getTruncationInfo,
  type InlineContentRendererProps,
  type TruncationInfo,
} from './InlineContentRenderer';
