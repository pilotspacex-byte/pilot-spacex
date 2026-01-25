/**
 * useAIContext - Hook for fetching and managing AI-generated context for an issue.
 *
 * T211: Provides context data, generation, regeneration, and task updates.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '@/services/api';
import type { AIContextData } from '@/components/issues/AIContext';
import type { TaskItem } from '@/components/issues/TaskChecklist';

// ============================================================================
// Query Keys
// ============================================================================

export const aiContextKeys = {
  all: ['ai-context'] as const,
  detail: (issueId: string) => [...aiContextKeys.all, issueId] as const,
  chat: (issueId: string) => [...aiContextKeys.all, issueId, 'chat'] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function getAIContext(issueId: string): Promise<AIContextData | null> {
  try {
    return await apiClient.get<AIContextData>(`/issues/${issueId}/ai-context`);
  } catch (error) {
    // Return null if no context exists (404)
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    throw error;
  }
}

async function generateAIContext(issueId: string): Promise<AIContextData> {
  return apiClient.post<AIContextData>(`/issues/${issueId}/ai-context/generate`);
}

async function regenerateAIContext(issueId: string): Promise<AIContextData> {
  return apiClient.post<AIContextData>(`/issues/${issueId}/ai-context/regenerate`);
}

async function updateContextTask(
  issueId: string,
  taskId: string,
  updates: Partial<TaskItem>
): Promise<TaskItem> {
  return apiClient.patch<TaskItem>(`/issues/${issueId}/ai-context/tasks/${taskId}`, updates);
}

// ============================================================================
// Hook
// ============================================================================

export interface UseAIContextOptions {
  /** Whether to fetch context on mount */
  enabled?: boolean;
}

export interface UseAIContextReturn {
  /** AI context data */
  data: AIContextData | null | undefined;
  /** Whether data is loading */
  isLoading: boolean;
  /** Error from fetch */
  error: Error | null;
  /** Generate context for the first time */
  generate: () => void;
  /** Whether generation is in progress */
  isGenerating: boolean;
  /** Regenerate context (refresh) */
  regenerate: () => void;
  /** Whether regeneration is in progress */
  isRegenerating: boolean;
  /** Update a task in the checklist */
  updateTask: (taskId: string, updates: Partial<TaskItem>) => void;
  /** Whether task update is in progress */
  isUpdatingTask: boolean;
  /** Refetch context data */
  refetch: () => void;
}

export function useAIContext(issueId: string, options?: UseAIContextOptions): UseAIContextReturn {
  const { enabled = true } = options ?? {};
  const queryClient = useQueryClient();

  // Query: Get AI context
  const query = useQuery({
    queryKey: aiContextKeys.detail(issueId),
    queryFn: () => getAIContext(issueId),
    enabled: enabled && !!issueId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation: Generate context
  const generateMutation = useMutation({
    mutationFn: () => generateAIContext(issueId),
    onSuccess: (data) => {
      queryClient.setQueryData(aiContextKeys.detail(issueId), data);
      toast.success('AI context generated');
    },
    onError: (error: Error) => {
      toast.error('Failed to generate AI context', {
        description: error.message,
      });
    },
  });

  // Mutation: Regenerate context
  const regenerateMutation = useMutation({
    mutationFn: () => regenerateAIContext(issueId),
    onSuccess: (data) => {
      queryClient.setQueryData(aiContextKeys.detail(issueId), data);
      toast.success('AI context regenerated');
    },
    onError: (error: Error) => {
      toast.error('Failed to regenerate AI context', {
        description: error.message,
      });
    },
  });

  // Mutation: Update task
  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, updates }: { taskId: string; updates: Partial<TaskItem> }) =>
      updateContextTask(issueId, taskId, updates),
    onSuccess: (updatedTask) => {
      // Optimistically update the task in the cache
      queryClient.setQueryData<AIContextData | null>(aiContextKeys.detail(issueId), (old) => {
        if (!old) return old;
        return {
          ...old,
          tasksChecklist: old.tasksChecklist.map((task) =>
            task.id === updatedTask.id ? updatedTask : task
          ),
        };
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to update task', {
        description: error.message,
      });
      // Refetch to get correct state
      query.refetch();
    },
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    generate: () => generateMutation.mutate(),
    isGenerating: generateMutation.isPending,
    regenerate: () => regenerateMutation.mutate(),
    isRegenerating: regenerateMutation.isPending,
    updateTask: (taskId, updates) => updateTaskMutation.mutate({ taskId, updates }),
    isUpdatingTask: updateTaskMutation.isPending,
    refetch: () => query.refetch(),
  };
}

export default useAIContext;
