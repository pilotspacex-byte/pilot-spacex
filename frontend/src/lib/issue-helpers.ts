import type { IssueState, StateBrief } from '@/types';

const VALID_STATES: Set<string> = new Set([
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'done',
  'cancelled',
]);

/**
 * Normalize a StateBrief.name to an IssueState key.
 * Returns 'backlog' as fallback for unrecognized state names.
 *
 * @example stateNameToKey("In Progress") → "in_progress"
 * @example stateNameToKey("Done") → "done"
 * @example stateNameToKey("Unknown") → "backlog"
 */
export function stateNameToKey(name: string | undefined | null): IssueState {
  if (!name) return 'backlog';
  const key = name.toLowerCase().replace(/\s+/g, '_').trim().replace(/^_|_$/g, '');
  return (VALID_STATES.has(key) ? key : 'backlog') as IssueState;
}

/**
 * Extract the IssueState key from an issue's state field.
 * Handles both formats:
 * - StateBrief object: { id, name, color, group } → uses name
 * - Plain string from API: "backlog", "in_progress" → uses directly
 */
export function getIssueStateKey(state: StateBrief | string | undefined | null): IssueState {
  if (!state) return 'backlog';
  if (typeof state === 'string') return stateNameToKey(state);
  return stateNameToKey(state.name);
}
