import type { IssueState } from '@/types';

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
