import type { IssueState } from '@/types';

/**
 * Normalize a StateBrief.name to an IssueState key.
 *
 * @example stateNameToKey("In Progress") → "in_progress"
 * @example stateNameToKey("Done") → "done"
 */
export function stateNameToKey(name: string): IssueState {
  return name.toLowerCase().replace(/\s+/g, '_') as IssueState;
}
