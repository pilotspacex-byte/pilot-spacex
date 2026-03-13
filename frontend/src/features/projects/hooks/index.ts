/**
 * Project hooks index.
 *
 * T008: TanStack Query hooks for projects feature.
 */

// List hooks
export {
  useProjects,
  usePrefetchProjects,
  projectsKeys,
  selectAllProjects,
  PROJECTS_QUERY_KEY,
  type UseProjectsOptions,
} from './useProjects';

// Detail hooks
export { useProject, type UseProjectOptions } from './useProject';

// Mutation hooks
export {
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  type UseCreateProjectOptions,
  type UseUpdateProjectOptions,
  type UseDeleteProjectOptions,
} from './useCreateProject';

// Knowledge graph hooks
export { useProjectKnowledgeGraph, projectKnowledgeGraphKeys } from './useProjectKnowledgeGraph';
