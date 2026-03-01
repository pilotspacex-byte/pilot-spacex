/**
 * useCreateBranch - Mutation hook for creating a GitHub branch from an issue.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { integrationsApi } from '@/services/api/integrations';
import { issueLinksKeys } from './use-issue-links';

export interface CreateBranchVars {
  workspaceId: string;
  issueId: string;
  integrationId: string;
  repository: string;
  branchName: string;
  baseBranch?: string;
}

export function useCreateBranch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      issueId,
      integrationId,
      repository,
      branchName,
      baseBranch,
    }: CreateBranchVars) =>
      integrationsApi.createBranch(workspaceId, issueId, integrationId, {
        repository,
        branch_name: branchName,
        base_branch: baseBranch ?? 'main',
      }),
    onSuccess: (_, vars) => {
      void queryClient.invalidateQueries({
        queryKey: issueLinksKeys.byWorkspace(vars.workspaceId, vars.issueId),
      });
      toast.success('Branch created', { description: vars.branchName });
    },
    onError: (error: Error) => {
      toast.error('Failed to create branch', { description: error.message });
    },
  });
}
