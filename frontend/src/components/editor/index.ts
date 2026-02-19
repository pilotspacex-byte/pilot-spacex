/**
 * Editor Components - Barrel Export
 */

export { NoteCanvas } from './NoteCanvas';
export type { NoteCanvasProps } from './NoteCanvas';

export { MarginAnnotations } from './MarginAnnotations';
export type { MarginAnnotationsProps } from './MarginAnnotations';

export { AutoTOC } from './AutoTOC';
export type { AutoTOCProps } from './AutoTOC';

export { SelectionToolbar } from './SelectionToolbar';
export type { SelectionToolbarProps } from './SelectionToolbar';

export { ThreadedDiscussion } from './ThreadedDiscussion';
export type { ThreadedDiscussionProps, Discussion, DiscussionComment } from './ThreadedDiscussion';

export { RichNoteHeader } from './RichNoteHeader';
export type { RichNoteHeaderProps } from './RichNoteHeader';

export { InlineNoteHeader } from './InlineNoteHeader';
export type { InlineNoteHeaderProps } from './InlineNoteHeader';

export { NoteTitleBlock } from './NoteTitleBlock';
export type { NoteTitleBlockProps } from './NoteTitleBlock';

export { VersionHistoryPanel } from './VersionHistoryPanel';
export type { VersionHistoryPanelProps, NoteVersion } from './VersionHistoryPanel';

export { IssueBox } from './IssueBox';
export type { IssueBoxProps, IssueType, IssueStatus } from './IssueBox';

export { AIThreadIndicator } from './AIThreadIndicator';
export type { AIThreadIndicatorProps, AIThreadArtifact } from './AIThreadIndicator';

export { AskPilotInput } from './AskPilotInput';
export type { AskPilotInputProps } from './AskPilotInput';

export { LargeNoteWarning } from './LargeNoteWarning';
export type { LargeNoteWarningProps } from './LargeNoteWarning';

export {
  SidebarPanel,
  SidebarPanelHeader,
  SidebarPanelContent,
  useSidebarPanel,
  SIDEBAR_DEFAULTS,
} from './sidebar';
export type {
  SidebarPanelProps,
  SidebarPanelHeaderProps,
  SidebarTab,
  SidebarPanelContentProps,
  SidebarPanelId,
  SidebarPanelControls,
} from './sidebar';
