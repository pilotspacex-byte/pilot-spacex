/**
 * audit-labels.ts — Human-readable label formatters for audit log entries.
 *
 * Backend services write resource_type and action as raw strings (e.g. "ISSUE",
 * "WORKSPACE_MEMBER", "issue.create"). These helpers map them to UI-friendly labels.
 */

/**
 * Map raw resource_type strings (UPPERCASE or lowercase from backend) to UI labels.
 */
const RESOURCE_TYPE_LABELS: Record<string, string> = {
  // Uppercase variants (written by most backend services)
  ISSUE: 'Issue',
  NOTE: 'Note',
  MEMBER: 'Member',
  WORKSPACE_MEMBER: 'Member',
  WORKSPACE: 'Workspace',
  ROLE: 'Role',
  SETTINGS: 'Settings',
  AI: 'AI',
  CYCLE: 'Cycle',
  PROJECT: 'Project',
  TASK: 'Task',
  COMMENT: 'Comment',
  LABEL: 'Label',
  // Lowercase variants (forward-compat / legacy)
  issue: 'Issue',
  note: 'Note',
  member: 'Member',
  workspace: 'Workspace',
  role: 'Role',
  settings: 'Settings',
  ai: 'AI',
};

/**
 * Map raw dot-notation action strings to UI-friendly labels.
 */
const ACTION_LABELS: Record<string, string> = {
  'issue.create': 'Issue Created',
  'issue.update': 'Issue Updated',
  'issue.delete': 'Issue Deleted',
  'note.create': 'Note Created',
  'note.update': 'Note Updated',
  'note.delete': 'Note Deleted',
  'member.invite': 'Member Invited',
  'member.remove': 'Member Removed',
  'role.assign': 'Role Assigned',
  'settings.update': 'Settings Updated',
  'ai.action': 'AI Action',
  'ai.rollback': 'AI Rollback',
};

/**
 * Format a raw resource_type string for UI display.
 * Unknown types fall back to title-casing the underscore-separated words.
 */
export function formatResourceType(raw: string | null): string {
  if (!raw) return '\u2014';
  return (
    RESOURCE_TYPE_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/**
 * Format a raw action string for UI display.
 * Unknown actions fall back to the raw string.
 */
export function formatAction(raw: string | null): string {
  if (!raw) return '\u2014';
  return ACTION_LABELS[raw] ?? raw;
}
