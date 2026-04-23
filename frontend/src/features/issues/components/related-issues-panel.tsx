'use client';

/**
 * RelatedIssuesPanel - AI-suggested and manually linked related issues.
 *
 * Renders two subsections inside a CollapsibleSection:
 * 1. AI Suggestions — semantically similar issues with reason badges and dismiss buttons.
 * 2. Linked Issues — manually linked RELATED IssueRelations with unlink buttons and a search combobox.
 *
 * MobX: observer() is correct here — no TipTap NodeViewRenderer involvement.
 */

import * as React from 'react';
import { useDeferredValue } from 'react';
import { observer } from 'mobx-react-lite';
import { Link2, Trash2, X, Plus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { issuesApi } from '@/services/api';
import { CollapsibleSection } from '@/features/issues/components/collapsible-section';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { useRelatedSuggestions } from '@/features/issues/hooks/use-related-suggestions';
import { useDismissSuggestion } from '@/features/issues/hooks/use-dismiss-suggestion';
import { useIssueRelations } from '@/features/issues/hooks/use-issue-relations';
import { useCreateRelation } from '@/features/issues/hooks/use-create-relation';
import { useDeleteRelation } from '@/features/issues/hooks/use-delete-relation';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RelatedIssuesPanelProps {
  workspaceId: string;
  issueId: string;
  workspaceSlug: string;
}

// ---------------------------------------------------------------------------
// Link Issue Combobox
// ---------------------------------------------------------------------------

interface LinkIssueComboboxProps {
  workspaceId: string;
  issueId: string;
  onSelect: (targetIssueId: string) => void;
}

function LinkIssueCombobox({ workspaceId, issueId, onSelect }: LinkIssueComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const deferredSearch = useDeferredValue(search);

  const { data: searchResult } = useQuery({
    queryKey: ['issues', workspaceId, 'search', deferredSearch],
    queryFn: () => issuesApi.list(workspaceId, { search: deferredSearch }, 1, 10),
    enabled: open && deferredSearch.length >= 1,
    staleTime: 10_000,
  });

  const results = searchResult?.items ?? [];

  const handleSelect = (id: string) => {
    onSelect(id);
    setSearch('');
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className={cn(
            'mt-2 flex w-full items-center gap-1.5 rounded-md px-2 py-1.5',
            'text-xs text-muted-foreground hover:bg-accent hover:text-foreground',
            'border border-dashed border-border',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          )}
          aria-label="Link issue"
        >
          <Plus className="size-3.5" />
          Link issue
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search tasks..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>
              {search.length === 0 ? 'Type to search tasks…' : 'No tasks found'}
            </CommandEmpty>
            {results.length > 0 && (
              <CommandGroup heading="Tasks">
                {results
                  .filter((issue) => issue.id !== issueId)
                  .map((issue) => (
                    <CommandItem
                      key={issue.id}
                      value={issue.id}
                      onSelect={() => handleSelect(issue.id)}
                      className="flex flex-col items-start gap-0.5"
                    >
                      <span className="flex items-center gap-1.5 text-sm">
                        <span className="text-xs text-muted-foreground">{issue.identifier}</span>
                        <span>{issue.name}</span>
                      </span>
                    </CommandItem>
                  ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const RelatedIssuesPanel = observer(function RelatedIssuesPanel({
  workspaceId,
  issueId,
  workspaceSlug: _workspaceSlug,
}: RelatedIssuesPanelProps) {
  const { data: suggestions = [], isLoading: suggestionsLoading } = useRelatedSuggestions(
    workspaceId,
    issueId
  );
  const dismiss = useDismissSuggestion(workspaceId, issueId);

  const { data: relations = [] } = useIssueRelations(workspaceId, issueId);
  const relatedLinks = relations.filter((r) => r.linkType === 'related');

  const deleteRelation = useDeleteRelation(workspaceId, issueId);
  const createRelation = useCreateRelation(workspaceId, issueId);

  const totalCount = suggestions.length + relatedLinks.length;

  return (
    <CollapsibleSection
      title="Related Tasks"
      icon={<Link2 className="size-4 text-muted-foreground" />}
      defaultOpen={true}
      count={totalCount > 0 ? totalCount : undefined}
    >
      {/* ---- AI Suggestions ---- */}
      <div className="mb-3">
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">AI Suggestions</p>
        {suggestionsLoading && (
          <p className="py-1 text-xs text-muted-foreground">Loading suggestions…</p>
        )}
        {!suggestionsLoading && suggestions.length === 0 && (
          <p className="py-2 text-xs text-muted-foreground">No suggestions yet</p>
        )}
        {suggestions.map((s) => (
          <div key={s.id} className="flex items-start justify-between gap-2 py-1.5 text-sm">
            <div className="min-w-0 flex-1">
              <span className="mr-1 text-xs text-muted-foreground">{s.identifier}</span>
              <span className="text-sm">{s.title}</span>
              <span className="ml-2 inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {s.reason}
              </span>
            </div>
            <button
              onClick={() => dismiss.mutate(s.id)}
              aria-label="Dismiss suggestion"
              className={cn(
                'shrink-0 rounded p-0.5',
                'text-muted-foreground hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* ---- Linked Issues ---- */}
      <div>
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">Linked Tasks</p>
        {relatedLinks.length === 0 && (
          <p className="py-1 text-xs text-muted-foreground">No linked tasks</p>
        )}
        {relatedLinks.map((link) => (
          <div key={link.id} className="flex items-center justify-between gap-2 py-1.5 text-sm">
            <div className="min-w-0 flex-1">
              <span className="mr-1 text-xs text-muted-foreground">
                {link.relatedIssue.identifier}
              </span>
              <span className="text-sm">{link.relatedIssue.name}</span>
            </div>
            <button
              onClick={() => deleteRelation.mutate(link.id)}
              aria-label="Unlink issue"
              className={cn(
                'shrink-0 rounded p-0.5',
                'text-muted-foreground hover:text-destructive',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
        ))}

        <LinkIssueCombobox
          workspaceId={workspaceId}
          issueId={issueId}
          onSelect={(targetIssueId) => createRelation.mutate(targetIssueId)}
        />
      </div>
    </CollapsibleSection>
  );
});
