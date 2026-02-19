/**
 * Shared PM block utilities - barrel export.
 *
 * MemberPicker: Workspace member selector with avatars (FR-014)
 * DatePicker: Date input with calendar popup and overdue badge (FR-015)
 * useBlockEditGuard: Hook tracking user edits on PM blocks (FR-048)
 * AIInsightBadge: Traffic-light badge for PM block AI insights (FR-056–059)
 */
export { MemberPicker } from './MemberPicker';
export type { MemberPickerProps } from './MemberPicker';

export { DatePicker } from './DatePicker';
export type { DatePickerProps } from './DatePicker';

export { useBlockEditGuard } from './useBlockEditGuard';
export type { BlockEditGuard } from './useBlockEditGuard';

export { AIInsightBadge } from './AIInsightBadge';
export type { AIInsightBadgeProps } from './AIInsightBadge';
