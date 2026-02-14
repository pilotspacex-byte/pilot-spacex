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

  // Sync with external prop changes
  React.useEffect(() => {
    setContent(value);
  }, [value]);

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
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const scheduleSave = React.useCallback(
    (nextContent: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        mutation.mutate(nextContent);
      }, DEBOUNCE_MS);
    },
    [mutation]
  );

  // Cleanup debounce on unmount
  React.useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
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
