/**
 * Skill types — mirror backend SkillResponse / SkillDetailResponse / ReferenceFileMeta.
 *
 * Decision (D-91-02-A): wire-format snake_case is preserved client-side because
 * the project has no global key transformer; `services/api/user-skills.ts` and
 * other AI-domain clients already follow this pattern (skill_content, is_active,
 * created_at). A camelCase translation layer would break that consistency for a
 * single phase.
 *
 * Decision (D-91-02-B): the gallery hook is named `useSkillCatalog` (not
 * `useSkills`) to avoid collision with the pre-existing
 * `frontend/src/features/ai/ChatView/hooks/useSkills.ts` consumed by the chat
 * composer. See `frontend/src/features/skills/hooks/useSkillCatalog.ts`.
 */

export interface Skill {
  name: string;
  description: string;
  category: string;
  icon: string;
  examples: string[];
  slug: string;
  feature_module: string[] | null;
  reference_files: string[];
  /** ISO 8601 datetime; backend returns max mtime of the skill dir's files. */
  updated_at: string | null;
}

export interface ReferenceFileMeta {
  name: string;
  path: string;
  size_bytes: number;
  mime_type: string;
}

/**
 * `SkillDetail` mirrors backend `SkillDetailResponse` — the detail endpoint
 * promotes `reference_files` from `string[]` to `ReferenceFileMeta[]` and adds
 * the markdown `body`. `Omit<Skill, 'reference_files'>` ensures the override is
 * type-safe rather than accidentally widening the parent.
 */
export interface SkillDetail extends Omit<Skill, 'reference_files'> {
  body: string;
  reference_files: ReferenceFileMeta[];
}
