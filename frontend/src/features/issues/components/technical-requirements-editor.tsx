'use client';

import * as React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Textarea } from '@/components/ui/textarea';
import { issuesApi } from '@/services/api';
import { issueDetailKeys } from '@/features/issues/hooks/use-issue-detail';
import type { Issue } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface TechnicalRequirementsEditorProps {
  issueId: string;
  workspaceId: string;
  value: string;
}

// ============================================================================
// Constants
// ============================================================================

const DEBOUNCE_MS = 2000;

// ============================================================================
// Component
// ============================================================================

export function TechnicalRequirementsEditor({
  issueId,
  workspaceId,
  value,
}: TechnicalRequirementsEditorProps) {
  const queryClient = useQueryClient();
  const queryKey = issueDetailKeys.detail(issueId);

  const [content, setContent] = React.useState(value);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  // H-9: Track pending data for flush-on-unmount
  const pendingDataRef = React.useRef<string | null>(null);
  // M-11: Track dirty state to skip prop sync
  const isDirtyRef = React.useRef(false);

  const mutation = useMutation({
    mutationFn: (technicalRequirements: string) =>
      issuesApi.update(workspaceId, issueId, { technicalRequirements }),

    onMutate: async (newValue) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<Issue>(queryKey);

      if (previous) {
        queryClient.setQueryData<Issue>(queryKey, {
          ...previous,
          technicalRequirements: newValue,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previous };
    },

    onError: (_err, _data, context) => {
      if (context?.previous) {
        queryClient.setQueryData<Issue>(queryKey, context.previous);
        setContent(context.previous.technicalRequirements ?? '');
      }
    },

    onSettled: () => {
      isDirtyRef.current = false;
      pendingDataRef.current = null;
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // H-7: Stable ref for mutation.mutate
  const mutateRef = React.useRef(mutation.mutate);
  React.useEffect(() => {
    mutateRef.current = mutation.mutate;
  }, [mutation.mutate]);

  // M-11: Only sync props when not dirty
  React.useEffect(() => {
    if (!isDirtyRef.current) {
      setContent(value);
    }
  }, [value]);

  const scheduleSave = React.useCallback((nextContent: string) => {
    isDirtyRef.current = true;
    pendingDataRef.current = nextContent;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      pendingDataRef.current = null;
      isDirtyRef.current = false;
      mutateRef.current(nextContent);
    }, DEBOUNCE_MS);
  }, []);

  // H-9: Flush pending save on unmount instead of canceling
  React.useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      if (pendingDataRef.current !== null) {
        mutateRef.current(pendingDataRef.current);
      }
    };
  }, []);

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const next = e.target.value;
      setContent(next);
      scheduleSave(next);
    },
    [scheduleSave]
  );

  return (
    <section aria-label="Technical requirements">
      <h3 className="text-sm font-medium mb-2">Technical Requirements</h3>
      <Textarea
        value={content}
        onChange={handleChange}
        placeholder="Describe technical requirements, constraints, and implementation notes (supports markdown)..."
        className="min-h-[120px] text-sm font-mono resize-y"
        aria-label="Technical requirements (markdown)"
      />
      <p className="text-xs text-muted-foreground mt-1">Supports markdown formatting</p>
    </section>
  );
}
