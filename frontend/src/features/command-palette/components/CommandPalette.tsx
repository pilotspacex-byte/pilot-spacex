'use client';

import { useState, useCallback, useMemo } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command';
import { Badge } from '@/components/ui/badge';
import { getAllActions } from '../registry/ActionRegistry';
import { useRecentActions } from '../hooks/useRecentActions';
import type { ActionCategory, PaletteAction } from '../types';

/**
 * Simple fuzzy match: checks if all characters of query appear in target
 * in order (case-insensitive).
 */
function fuzzyMatch(query: string, target: string): boolean {
  if (!query) return true;
  const lowerQuery = query.toLowerCase();
  const lowerTarget = target.toLowerCase();
  let qi = 0;
  for (let ti = 0; ti < lowerTarget.length && qi < lowerQuery.length; ti++) {
    if (lowerTarget[ti] === lowerQuery[qi]) {
      qi++;
    }
  }
  return qi === lowerQuery.length;
}

const CATEGORY_LABELS: Record<ActionCategory, string> = {
  file: 'File',
  edit: 'Edit',
  view: 'View',
  navigate: 'Navigate',
  note: 'Note',
  ai: 'AI',
};

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const { addRecent, getRecent } = useRecentActions();

  const allActions = useMemo(() => {
    if (!isOpen) return [];
    return getAllActions();
  }, [isOpen]);

  const recentIds = useMemo(() => {
    if (!isOpen) return [];
    return getRecent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const filteredActions = useMemo(() => {
    if (!query) return allActions;
    return allActions.filter((action) => fuzzyMatch(query, action.label));
  }, [query, allActions]);

  const recentActions = useMemo(() => {
    if (query) return [];
    return recentIds
      .map((id) => allActions.find((a) => a.id === id))
      .filter((a): a is PaletteAction => a !== undefined);
  }, [query, recentIds, allActions]);

  // Group filtered actions by category
  const groupedActions = useMemo(() => {
    const groups = new Map<ActionCategory, PaletteAction[]>();
    for (const action of filteredActions) {
      const existing = groups.get(action.category) ?? [];
      existing.push(action);
      groups.set(action.category, existing);
    }
    return groups;
  }, [filteredActions]);

  const handleSelect = useCallback(
    (action: PaletteAction) => {
      action.execute();
      addRecent(action.id);
      onClose();
    },
    [addRecent, onClose]
  );

  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) {
        onClose();
      }
    },
    [onClose]
  );

  // Reset query when palette opens
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
  }, []);

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-[640px] w-[calc(100%-32px)] top-12 translate-y-0 p-0 gap-0"
        aria-describedby={undefined}
      >
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Type a command..."
            value={query}
            onValueChange={handleQueryChange}
            className="h-10"
            autoFocus
          />
          <CommandList className="max-h-[400px]">
            <CommandEmpty>
              <div className="flex flex-col items-center gap-1 py-6 text-center">
                <p className="text-sm font-medium">No matching actions</p>
                <p className="text-xs text-muted-foreground">Try a different search term.</p>
              </div>
            </CommandEmpty>

            {recentActions.length > 0 && (
              <CommandGroup heading="Recently Used">
                {recentActions.map((action) => (
                  <PaletteItem
                    key={`recent-${action.id}`}
                    action={action}
                    onSelect={handleSelect}
                  />
                ))}
              </CommandGroup>
            )}

            {Array.from(groupedActions.entries()).map(([category, actions]) => (
              <CommandGroup key={category} heading={CATEGORY_LABELS[category]}>
                {actions.map((action) => (
                  <PaletteItem key={action.id} action={action} onSelect={handleSelect} />
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

function PaletteItem({
  action,
  onSelect,
}: {
  action: PaletteAction;
  onSelect: (action: PaletteAction) => void;
}) {
  const Icon = action.icon;
  return (
    <CommandItem value={action.id} onSelect={() => onSelect(action)}>
      <Icon className="size-4 shrink-0" />
      <span className="flex-1 truncate">{action.label}</span>
      <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5">
        {CATEGORY_LABELS[action.category]}
      </Badge>
      {action.shortcut && <CommandShortcut>{action.shortcut}</CommandShortcut>}
    </CommandItem>
  );
}
