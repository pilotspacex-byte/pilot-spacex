'use client';

import * as React from 'react';
import { Check, Plus, X, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { AIConfidenceTag } from '@/components/ai/AIConfidenceTag';
import type { LabelBrief as Label } from '@/types';

export interface LabelSuggestion {
  name: string;
  confidence: number;
  isExisting: boolean;
}

export interface LabelSelectorProps {
  /** Currently selected labels */
  selectedLabels: Label[];
  /** Available labels to choose from */
  availableLabels: Label[];
  /** AI-suggested labels */
  suggestions?: LabelSuggestion[];
  /** Called when labels change */
  onChange: (labels: Label[]) => void;
  /** Called when a suggestion is accepted */
  onSuggestionAccept?: (suggestion: LabelSuggestion) => void;
  /** Called when a suggestion is rejected */
  onSuggestionReject?: (suggestion: LabelSuggestion) => void;
  /** Called when creating a new label */
  onCreateLabel?: (name: string) => Promise<Label>;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  className?: string;
}

/**
 * LabelSelector provides a searchable, multi-select dropdown for labels.
 * Supports AI suggestions and creating new labels.
 *
 * @example
 * ```tsx
 * <LabelSelector
 *   selectedLabels={labels}
 *   availableLabels={allLabels}
 *   suggestions={aiSuggestions}
 *   onChange={setLabels}
 *   onCreateLabel={createNewLabel}
 * />
 * ```
 */
export function LabelSelector({
  selectedLabels,
  availableLabels,
  suggestions = [],
  onChange,
  onSuggestionAccept,
  onSuggestionReject,
  onCreateLabel,
  disabled = false,
  placeholder = 'Add labels...',
  className,
}: LabelSelectorProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [isCreating, setIsCreating] = React.useState(false);

  const selectedIds = new Set(selectedLabels.map((l) => l.id));

  // Filter suggestions to only show unselected ones
  const activeSuggestions = suggestions.filter(
    (s) => !selectedLabels.some((l) => l.name.toLowerCase() === s.name.toLowerCase())
  );

  // Filter available labels by search
  const filteredLabels = availableLabels.filter((label) =>
    label.name.toLowerCase().includes(search.toLowerCase())
  );

  // Check if search term matches any existing label
  const canCreate =
    search.trim() &&
    onCreateLabel &&
    !availableLabels.some((l) => l.name.toLowerCase() === search.toLowerCase());

  const handleSelect = (label: Label) => {
    if (selectedIds.has(label.id)) {
      onChange(selectedLabels.filter((l) => l.id !== label.id));
    } else {
      // Check if this was a suggested label
      const suggestion = suggestions.find((s) => s.name.toLowerCase() === label.name.toLowerCase());
      if (suggestion) {
        onSuggestionAccept?.(suggestion);
      }
      onChange([...selectedLabels, label]);
    }
  };

  const handleRemove = (label: Label) => {
    onChange(selectedLabels.filter((l) => l.id !== label.id));
  };

  const handleCreate = async () => {
    if (!canCreate || !onCreateLabel) return;

    setIsCreating(true);
    try {
      const newLabel = await onCreateLabel(search.trim());
      onChange([...selectedLabels, newLabel]);
      setSearch('');
    } finally {
      setIsCreating(false);
    }
  };

  const handleSuggestionClick = (suggestion: LabelSuggestion) => {
    const existingLabel = availableLabels.find(
      (l) => l.name.toLowerCase() === suggestion.name.toLowerCase()
    );

    if (existingLabel) {
      handleSelect(existingLabel);
    } else if (onCreateLabel) {
      // Create the suggested label
      onCreateLabel(suggestion.name).then((newLabel) => {
        onSuggestionAccept?.(suggestion);
        onChange([...selectedLabels, newLabel]);
      });
    }
  };

  const handleSuggestionDismiss = (suggestion: LabelSuggestion, e: React.MouseEvent) => {
    e.stopPropagation();
    onSuggestionReject?.(suggestion);
  };

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Selected labels */}
      {selectedLabels.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selectedLabels.map((label) => (
            <Badge
              key={label.id}
              variant="secondary"
              className="gap-1 pr-1"
              style={{
                backgroundColor: `${label.color}20`,
                color: label.color,
                borderColor: `${label.color}40`,
              }}
            >
              {label.name}
              <button
                type="button"
                onClick={() => handleRemove(label)}
                className="ml-0.5 rounded-full p-0.5 hover:bg-black/10"
                disabled={disabled}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* AI Suggestions */}
      {activeSuggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Sparkles className="size-3 text-ai" />
            Suggested:
          </span>
          {activeSuggestions.map((suggestion) => (
            <Badge
              key={suggestion.name}
              variant="outline"
              className="cursor-pointer gap-1 pr-1 transition-colors hover:bg-ai/10"
              onClick={() => handleSuggestionClick(suggestion)}
            >
              <span className="flex items-center gap-1">
                {suggestion.name}
                <AIConfidenceTag confidence={suggestion.confidence} className="ml-0.5 px-1 py-0" />
              </span>
              <button
                type="button"
                onClick={(e) => handleSuggestionDismiss(suggestion, e)}
                className="ml-0.5 rounded-full p-0.5 hover:bg-black/10"
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Label selector popover */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            disabled={disabled}
            className="w-fit justify-start gap-2"
          >
            <Plus className="size-4" />
            {placeholder}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput placeholder="Search labels..." value={search} onValueChange={setSearch} />
            <CommandList>
              <CommandEmpty>
                {canCreate ? (
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 p-2 text-sm hover:bg-accent"
                    onClick={handleCreate}
                    disabled={isCreating}
                  >
                    <Plus className="size-4" />
                    Create &quot;{search}&quot;
                  </button>
                ) : (
                  <span className="p-2 text-sm text-muted-foreground">No labels found</span>
                )}
              </CommandEmpty>
              <CommandGroup>
                {filteredLabels.map((label) => {
                  const isSelected = selectedIds.has(label.id);
                  const suggestion = suggestions.find(
                    (s) => s.name.toLowerCase() === label.name.toLowerCase()
                  );

                  return (
                    <CommandItem
                      key={label.id}
                      value={label.name}
                      onSelect={() => handleSelect(label)}
                      className="flex items-center justify-between"
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className="size-3 rounded-full"
                          style={{ backgroundColor: label.color }}
                        />
                        {label.name}
                      </span>
                      <span className="flex items-center gap-1">
                        {suggestion && !isSelected && (
                          <AIConfidenceTag
                            confidence={suggestion.confidence}
                            showIcon
                            className="px-1 py-0 text-[10px]"
                          />
                        )}
                        {isSelected && <Check className="size-4" />}
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
              {canCreate && filteredLabels.length > 0 && (
                <>
                  <CommandSeparator />
                  <CommandGroup>
                    <CommandItem onSelect={handleCreate} disabled={isCreating}>
                      <Plus className="mr-2 size-4" />
                      Create &quot;{search}&quot;
                    </CommandItem>
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default LabelSelector;
