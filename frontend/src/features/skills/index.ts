/**
 * Phase 91 Plan 03 — public barrel for the skills feature.
 *
 * Hooks (Plan 02) are re-exported via `./hooks`. Components/lib added by
 * Plan 03 land here directly so consumers (route page, palette, chat slash
 * commands) can import from `@/features/skills`.
 */
export { SkillCard, type SkillCardProps } from './components/SkillCard';
export { SkillsGalleryPage } from './components/SkillsGalleryPage';
export { SkillDetailPage } from './components/SkillDetailPage';
export { SkillReferenceFiles } from './components/SkillReferenceFiles';
export { SkillFilePreview } from './components/SkillFilePreview';
export { resolveLucideIcon } from './lib/skill-icon';
export {
  encodeSkillFilePeek,
  decodeSkillFilePeek,
  SKILL_FILE_PEEK_PREFIX,
} from './lib/skill-peek';
export {
  useSkillCatalog,
  SKILLS_CATALOG_QUERY_KEY,
  useSkill,
  skillQueryKey,
  useSkillFileBlob,
  type SkillFileBlob,
  useSkillGraphData,
  type UseSkillGraphDataResult,
  useSkillGraphLayout,
  type UseSkillGraphLayoutResult,
  type FlowNodeData,
} from './hooks';
export { buildSkillGraph } from './lib/skill-graph';
export type {
  SkillGraphNode,
  SkillGraphEdge,
  SkillGraphResult,
} from './lib/skill-graph';
export {
  layoutSkillGraph,
  COLUMN_PITCH,
  ROW_PITCH,
} from './lib/skill-graph-layout';
