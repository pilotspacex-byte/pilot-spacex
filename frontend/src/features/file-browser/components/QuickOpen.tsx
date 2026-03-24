'use client';

import { useCallback, Fragment } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { useFileStore } from '@/stores/RootStore';
import { useQuickOpen, type QuickOpenResult } from '../hooks/useQuickOpen';
import type { FileTreeItem } from '../hooks/useFileTree';

/** Highlight matched characters in a string. */
function HighlightedText({ text, indices }: { text: string; indices: number[] }) {
  if (indices.length === 0) return <>{text}</>;
  const indexSet = new Set(indices);
  return (
    <>
      {text.split('').map((char, i) => (
        <Fragment key={i}>
          {indexSet.has(i) ? <span className="font-bold text-primary">{char}</span> : char}
        </Fragment>
      ))}
    </>
  );
}

/** Render a single result item. */
function QuickOpenItem({
  result,
  isSelected,
  onSelect,
}: {
  result: QuickOpenResult;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <CommandItem
      value={result.item.id}
      onSelect={onSelect}
      className={isSelected ? 'bg-accent' : ''}
    >
      <div className="flex flex-col gap-0.5">
        <span className="text-sm">
          <HighlightedText text={result.item.name} indices={result.nameIndices} />
        </span>
        <span className="text-xs text-muted-foreground font-mono">
          <HighlightedText text={result.item.path} indices={result.pathIndices} />
        </span>
      </div>
    </CommandItem>
  );
}

interface QuickOpenProps {
  items: FileTreeItem[];
}

export function QuickOpen({ items }: QuickOpenProps) {
  const fileStore = useFileStore();
  const { isOpen, close, query, setQuery, results, selectedIndex, selectCurrent } =
    useQuickOpen(items);

  const handleSelect = useCallback(
    (item: FileTreeItem) => {
      fileStore.openFile({
        id: item.id,
        name: item.name,
        path: item.path,
        source: item.source,
        language: item.language ?? 'plaintext',
        content: '',
        isReadOnly: item.source === 'remote',
      });
      close();
    },
    [fileStore, close]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const item = selectCurrent();
        if (item) handleSelect(item);
      }
    },
    [selectCurrent, handleSelect]
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent
        className="max-w-[560px] w-[calc(100%-32px)] top-12 translate-y-0 p-0 gap-0"
        aria-describedby={undefined}
      >
        <DialogTitle className="sr-only">Quick Open</DialogTitle>
        <Command shouldFilter={false} onKeyDown={handleKeyDown}>
          <CommandInput
            placeholder="Search files..."
            value={query}
            onValueChange={setQuery}
            className="h-10 font-mono"
            autoFocus
          />
          <CommandList className="max-h-[400px]">
            <CommandEmpty>
              <div className="flex flex-col items-center gap-1 py-6 text-center">
                <p className="text-sm font-medium">No matching files</p>
                <p className="text-xs text-muted-foreground">Try a different search term.</p>
              </div>
            </CommandEmpty>
            <CommandGroup>
              {results.map((result, index) => (
                <QuickOpenItem
                  key={result.item.id}
                  result={result}
                  isSelected={index === selectedIndex}
                  onSelect={() => handleSelect(result.item)}
                />
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
