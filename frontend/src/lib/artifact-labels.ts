/**
 * User-visible display labels for artifact types.
 *
 * Internal identifier keys (ISSUE, NOTE, ...) are the backend contract and MUST NOT change.
 * To surface a new display label, update this map — do NOT rename the backend.
 *
 * See .planning/PROJECT.md → "Out of Scope — Task/Topic Rename Cascade".
 */

export const ARTIFACT_TYPE_LABEL = {
  ISSUE: { singular: 'Task', plural: 'Tasks' },
  NOTE: { singular: 'Topic', plural: 'Topics' },
  SPEC: { singular: 'Spec', plural: 'Specs' },
  DECISION: { singular: 'Decision', plural: 'Decisions' },
  SKILL: { singular: 'Skill', plural: 'Skills' },
} as const;

export type ArtifactInternalType = keyof typeof ARTIFACT_TYPE_LABEL;

export function artifactLabel(type: ArtifactInternalType, plural = false): string {
  const entry = ARTIFACT_TYPE_LABEL[type];
  return plural ? entry.plural : entry.singular;
}
