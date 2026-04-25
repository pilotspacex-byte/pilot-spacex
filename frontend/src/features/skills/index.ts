/**
 * Phase 91 Plan 03 — public barrel for the skills feature.
 *
 * Hooks (Plan 02) are re-exported via `./hooks`. Components/lib added by
 * Plan 03 land here directly so consumers (route page, palette, chat slash
 * commands) can import from `@/features/skills`.
 */
export { SkillCard, type SkillCardProps } from './components/SkillCard';
export { SkillsGalleryPage } from './components/SkillsGalleryPage';
export { resolveLucideIcon } from './lib/skill-icon';
export {
  useSkillCatalog,
  SKILLS_CATALOG_QUERY_KEY,
  useSkill,
  skillQueryKey,
  useSkillFileBlob,
  type SkillFileBlob,
} from './hooks';
