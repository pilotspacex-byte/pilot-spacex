/**
 * Shared utilities for ChatView components.
 */

/** Convert snake_case action type to a human-readable title-case label. */
export function formatActionType(actionType: string): string {
  return actionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Destructive actions that require modal overlay approval per DD-003. */
export const DESTRUCTIVE_ACTIONS = new Set([
  'delete_issue',
  'merge_pr',
  'close_issue',
  'archive_workspace',
  'delete_note',
  'delete_comment',
  'unlink_issue_from_note',
  'unlink_issues',
]);

export function isDestructiveAction(actionType: string): boolean {
  return DESTRUCTIVE_ACTIONS.has(actionType);
}
