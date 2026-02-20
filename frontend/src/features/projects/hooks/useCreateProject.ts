'use client';

/**
 * useCreateProject - Mutation hooks for project CRUD.
 *
 * T007: Create, update, and delete projects with cache invalidation.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { projectsApi } from '@/services/api';
import type { CreateProjectData, UpdateProjectData } from '@/services/api/projects';
import type { Project } from '@/types';
import { projectsKeys } from './useProjects';

export interface UseCreateProjectOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: (project: Project) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseUpdateProjectOptions {
  /** Workspace ID for cache invalidation */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: (project: Project) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseDeleteProjectOptions {
  /** Workspace ID for cache invalidation */
  workspaceId: string;
  /** Callback on success */
  onSuccess?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for creating a new project
 */
export function useCreateProject({ workspaceId, onSuccess, onError }: UseCreateProjectOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectData) => projectsApi.create(workspaceId, data),

    onSuccess: (project) => {
      queryClient.invalidateQueries({
        queryKey: projectsKeys.list(workspaceId),
      });

      queryClient.setQueryData(projectsKeys.detail(project.id), project);

      toast.success('Project created', {
        description: `"${project.name}" has been created.`,
      });

      onSuccess?.(project);
    },

    onError: (error: Error) => {
      toast.error('Failed to create project', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for updating a project
 */
export function useUpdateProject({ workspaceId, onSuccess, onError }: UseUpdateProjectOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: string; data: UpdateProjectData }) =>
      projectsApi.update(projectId, data),

    onMutate: async ({ projectId, data }) => {
      await queryClient.cancelQueries({
        queryKey: projectsKeys.detail(projectId),
      });

      const previousProject = queryClient.getQueryData<Project>(projectsKeys.detail(projectId));

      if (previousProject) {
        queryClient.setQueryData(projectsKeys.detail(projectId), {
          ...previousProject,
          ...data,
        });
      }

      return { previousProject };
    },

    onSuccess: (project) => {
      queryClient.setQueryData(projectsKeys.detail(project.id), project);

      queryClient.invalidateQueries({
        queryKey: projectsKeys.list(workspaceId),
      });

      toast.success('Project updated', {
        description: `"${project.name}" has been updated.`,
      });

      onSuccess?.(project);
    },

    onError: (error: Error, { projectId }, context) => {
      if (context?.previousProject) {
        queryClient.setQueryData(projectsKeys.detail(projectId), context.previousProject);
      }

      toast.error('Failed to update project', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}

/**
 * Hook for deleting a project
 */
export function useDeleteProject({ workspaceId, onSuccess, onError }: UseDeleteProjectOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectsApi.delete(projectId),

    onMutate: async (projectId) => {
      await queryClient.cancelQueries({
        queryKey: projectsKeys.detail(projectId),
      });

      const previousProject = queryClient.getQueryData<Project>(projectsKeys.detail(projectId));

      queryClient.removeQueries({
        queryKey: projectsKeys.detail(projectId),
      });

      return { previousProject };
    },

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: projectsKeys.list(workspaceId),
      });

      toast.success('Project deleted');
      onSuccess?.();
    },

    onError: (error: Error, projectId, context) => {
      if (context?.previousProject) {
        queryClient.setQueryData(projectsKeys.detail(projectId), context.previousProject);
      }

      toast.error('Failed to delete project', {
        description: error.message,
      });
      onError?.(error);
    },
  });
}
