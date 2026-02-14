'use client';

import * as React from 'react';
import { Plus, X } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { issuesApi } from '@/services/api';
import { issueDetailKeys } from '@/features/issues/hooks/use-issue-detail';
import type { Issue } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface AcceptanceCriteriaEditorProps {
  issueId: string;
  workspaceId: string;
  criteria: string[];
}

// ============================================================================
// Constants
// ============================================================================

const DEBOUNCE_MS = 2000;

// ============================================================================
// Component
// ============================================================================

export function AcceptanceCriteriaEditor({
  issueId,
  workspaceId,
  criteria,
}: AcceptanceCriteriaEditorProps) {
  const queryClient = useQueryClient();
  const queryKey = issueDetailKeys.detail(issueId);

  const [items, setItems] = React.useState<string[]>(criteria);
  const [newItem, setNewItem] = React.useState('');
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync with external prop changes (e.g. after server refetch)
  React.useEffect(() => {
    setItems(criteria);
  }, [criteria]);

  const mutation = useMutation({
    mutationFn: (acceptanceCriteria: string[]) =>
      issuesApi.update(workspaceId, issueId, { acceptanceCriteria }),

    onMutate: async (newCriteria) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<Issue>(queryKey);

      if (previous) {
        queryClient.setQueryData<Issue>(queryKey, {
          ...previous,
          acceptanceCriteria: newCriteria,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previous };
    },

    onError: (_err, _data, context) => {
      if (context?.previous) {
        queryClient.setQueryData<Issue>(queryKey, context.previous);
        setItems(context.previous.acceptanceCriteria ?? []);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const scheduleSave = React.useCallback(
    (nextItems: string[]) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        mutation.mutate(nextItems);
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

  const handleAddItem = React.useCallback(() => {
    const trimmed = newItem.trim();
    if (!trimmed) return;
    const next = [...items, trimmed];
    setItems(next);
    setNewItem('');
    scheduleSave(next);
  }, [newItem, items, scheduleSave]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleAddItem();
      }
    },
    [handleAddItem]
  );

  const handleRemoveItem = React.useCallback(
    (index: number) => {
      const next = items.filter((_, i) => i !== index);
      setItems(next);
      scheduleSave(next);
    },
    [items, scheduleSave]
  );

  const handleEditItem = React.useCallback(
    (index: number, value: string) => {
      const next = items.map((item, i) => (i === index ? value : item));
      setItems(next);
      scheduleSave(next);
    },
    [items, scheduleSave]
  );

  return (
    <section aria-label="Acceptance criteria">
      <h3 className="text-sm font-medium mb-2">Acceptance Criteria</h3>

      {items.length > 0 && (
        <ul className="space-y-1.5 mb-2" role="list">
          {items.map((item, index) => (
            <li key={index} className="flex items-start gap-2 group">
              <Checkbox checked={false} disabled className="mt-1 shrink-0" aria-hidden="true" />
              <Input
                value={item}
                onChange={(e) => handleEditItem(index, e.target.value)}
                className="h-8 text-sm flex-1 border-transparent hover:border-border focus:border-border bg-transparent"
                aria-label={`Acceptance criterion ${index + 1}`}
              />
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => handleRemoveItem(index)}
                aria-label={`Remove criterion: ${item}`}
              >
                <X className="size-3.5" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2">
        <Input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add acceptance criterion..."
          className="h-8 text-sm flex-1"
          aria-label="New acceptance criterion"
        />
        <Button
          variant="ghost"
          size="sm"
          className="size-7 p-0 shrink-0"
          onClick={handleAddItem}
          disabled={!newItem.trim()}
          aria-label="Add criterion"
        >
          <Plus className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </section>
  );
}
