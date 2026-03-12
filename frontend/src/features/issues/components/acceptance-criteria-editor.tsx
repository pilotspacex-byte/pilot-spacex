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

interface StableItem {
  id: number;
  text: string;
}

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

  // H-8: Stable IDs for list items
  const nextIdRef = React.useRef(criteria.length);
  const toStableItems = React.useCallback((strings: string[]): StableItem[] => {
    return strings.map((text) => ({ id: nextIdRef.current++, text }));
  }, []);

  const [items, setItems] = React.useState<StableItem[]>(() =>
    criteria.map((text, i) => ({ id: i, text }))
  );
  const [newItem, setNewItem] = React.useState('');
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  // H-9: Track pending data for flush-on-unmount
  const pendingDataRef = React.useRef<string[] | null>(null);
  // M-11: Track dirty state to skip prop sync
  const isDirtyRef = React.useRef(false);

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
        setItems(toStableItems(context.previous.acceptanceCriteria ?? []));
      }
    },

    onSettled: () => {
      isDirtyRef.current = false;
      pendingDataRef.current = null;
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  // H-7: Stable ref for mutation.mutate to avoid re-creating scheduleSave
  const mutateRef = React.useRef(mutation.mutate);
  React.useEffect(() => {
    mutateRef.current = mutation.mutate;
  }, [mutation.mutate]);

  // M-11: Only sync props when not dirty
  React.useEffect(() => {
    if (!isDirtyRef.current) {
      setItems(toStableItems(criteria));
    }
  }, [criteria, toStableItems]);

  const scheduleSave = React.useCallback((nextItems: string[]) => {
    isDirtyRef.current = true;
    pendingDataRef.current = nextItems;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      pendingDataRef.current = null;
      isDirtyRef.current = false;
      mutateRef.current(nextItems);
    }, DEBOUNCE_MS);
  }, []);

  // H-9: Flush pending save on unmount instead of canceling
  React.useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      if (pendingDataRef.current) {
        mutateRef.current(pendingDataRef.current);
      }
    };
  }, []);

  const handleAddItem = React.useCallback(() => {
    const trimmed = newItem.trim();
    if (!trimmed) return;
    const newStable: StableItem = { id: nextIdRef.current++, text: trimmed };
    setItems((prev) => {
      const next = [...prev, newStable];
      scheduleSave(next.map((i) => i.text));
      return next;
    });
    setNewItem('');
  }, [newItem, scheduleSave]);

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
    (id: number) => {
      setItems((prev) => {
        const next = prev.filter((item) => item.id !== id);
        scheduleSave(next.map((i) => i.text));
        return next;
      });
    },
    [scheduleSave]
  );

  const handleEditItem = React.useCallback(
    (id: number, value: string) => {
      setItems((prev) => {
        const next = prev.map((item) => (item.id === id ? { ...item, text: value } : item));
        scheduleSave(next.map((i) => i.text));
        return next;
      });
    },
    [scheduleSave]
  );

  return (
    <section aria-label="Acceptance criteria">
      <h3 className="text-sm font-medium mb-2">Acceptance Criteria</h3>

      {items.length > 0 && (
        <ul className="space-y-1.5 mb-2" role="list">
          {items.map((item) => (
            <li key={item.id} className="flex items-start gap-2 group">
              <Checkbox checked={false} disabled className="mt-1 shrink-0" aria-hidden="true" />
              <Input
                value={item.text}
                onChange={(e) => handleEditItem(item.id, e.target.value)}
                className="h-8 text-sm flex-1 border-transparent hover:border-border focus:border-border bg-transparent"
                aria-label={`Acceptance criterion ${items.indexOf(item) + 1}`}
              />
              <Button
                variant="ghost"
                size="sm"
                className="size-7 p-0 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => handleRemoveItem(item.id)}
                aria-label={`Remove criterion: ${item.text}`}
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
