/**
 * TanStack Query hooks for skill graph CRUD operations.
 * Source: Phase 52, P52-03
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import {
  type SkillGraphUpdate,
  type SkillGraphDecompileRequest,
  skillGraphsApi,
} from '@/services/api/skill-graphs';

// ---------------------------------------------------------------------------
// Query Keys
// ---------------------------------------------------------------------------

export const skillGraphKeys = {
  all: ['skill-graph'] as const,
  byId: (graphId: string) => ['skill-graph', graphId] as const,
  byTemplate: (templateId: string) => ['skill-graph', 'by-template', templateId] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useSkillGraph(workspaceId: string, graphId: string | undefined) {
  return useQuery({
    queryKey: skillGraphKeys.byId(graphId ?? ''),
    queryFn: () => skillGraphsApi.getSkillGraph(workspaceId, graphId!),
    enabled: !!graphId && !!workspaceId,
    staleTime: 60_000,
  });
}

export function useSkillGraphByTemplate(
  workspaceId: string,
  templateId: string | undefined,
) {
  return useQuery({
    queryKey: skillGraphKeys.byTemplate(templateId ?? ''),
    queryFn: () => skillGraphsApi.getSkillGraphByTemplate(workspaceId, templateId!),
    enabled: !!templateId && !!workspaceId,
    staleTime: 60_000,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/**
 * Upsert a skill graph by template ID.
 * Creates the graph if it doesn't exist, updates it otherwise.
 */
export function useSkillGraphMutation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      templateId,
      data,
    }: {
      templateId: string;
      data: SkillGraphUpdate;
    }) => skillGraphsApi.upsertSkillGraphByTemplate(workspaceId, templateId, data),
    onSuccess: (_result, variables) => {
      void qc.invalidateQueries({ queryKey: skillGraphKeys.all });
      void qc.invalidateQueries({
        queryKey: skillGraphKeys.byTemplate(variables.templateId),
      });
    },
  });
}

/**
 * Preview execution trace for a skill graph.
 * Returns ordered list of nodes in topological execution order.
 */
export function usePreviewSkillGraph(workspaceId: string) {
  return useMutation({
    mutationFn: ({ graphId }: { graphId: string }) =>
      skillGraphsApi.previewSkillGraph(workspaceId, graphId),
  });
}

/**
 * Decompile SKILL.md content into a graph representation.
 * Returns React Flow-compatible nodes and edges.
 */
export function useDecompileSkillGraph(workspaceId: string) {
  return useMutation({
    mutationFn: (data: SkillGraphDecompileRequest) =>
      skillGraphsApi.decompileSkillGraph(workspaceId, data),
  });
}

/**
 * Compile a skill graph to SKILL.md content via AI synthesis.
 * Returns compiled content for preview.
 */
export function useCompileSkillGraph(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ graphId }: { graphId: string }) =>
      skillGraphsApi.compileSkillGraph(workspaceId, graphId),
    onSuccess: (_result, variables) => {
      toast.success('Graph compiled to SKILL.md');
      void qc.invalidateQueries({ queryKey: skillGraphKeys.all });
      void qc.invalidateQueries({
        queryKey: skillGraphKeys.byId(variables.graphId),
      });
    },
    onError: () => {
      toast.error('Compilation failed');
    },
  });
}

/**
 * Save (update) an existing skill graph by its ID.
 * Shows a sonner toast on success.
 */
export function useSaveSkillGraph(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      graphId,
      data,
    }: {
      graphId: string;
      data: SkillGraphUpdate;
    }) => skillGraphsApi.updateSkillGraph(workspaceId, graphId, data),
    onSuccess: (_result, variables) => {
      toast.success('Graph saved');
      void qc.invalidateQueries({ queryKey: skillGraphKeys.all });
      void qc.invalidateQueries({
        queryKey: skillGraphKeys.byId(variables.graphId),
      });
    },
  });
}
