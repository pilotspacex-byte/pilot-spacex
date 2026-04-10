/**
 * MemoryFacetBar — Horizontal filter bar for memory type, kind, pinned.
 *
 * Phase 71: Filter bar (NOT sidebar) to avoid settings modal width overflow.
 */

'use client';

import * as React from 'react';
import { FilterX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import type { MemoryListParams } from '../hooks/use-ai-memory';

type Filters = Pick<MemoryListParams, 'type' | 'kind' | 'pinned'>;

interface MemoryFacetBarProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

const NODE_TYPES = [
  'note_summary',
  'issue_decision',
  'agent_turn',
  'user_correction',
  'pr_review_finding',
  'note_chunk',
] as const;

const KINDS = ['raw', 'summary', 'turn', 'deny', 'finding'] as const;

export function MemoryFacetBar({ filters, onChange }: MemoryFacetBarProps) {
  const hasFilters = !!(filters.type?.length || filters.kind || filters.pinned != null);

  const handleTypeChange = React.useCallback(
    (value: string) => {
      onChange({
        ...filters,
        type: value === 'all' ? undefined : [value],
      });
    },
    [filters, onChange],
  );

  const handleKindChange = React.useCallback(
    (value: string) => {
      onChange({
        ...filters,
        kind: value === 'all' ? undefined : value,
      });
    },
    [filters, onChange],
  );

  const handlePinnedChange = React.useCallback(
    (checked: boolean | 'indeterminate') => {
      onChange({
        ...filters,
        pinned: checked === true ? true : undefined,
      });
    },
    [filters, onChange],
  );

  const handleClear = React.useCallback(() => {
    onChange({});
  }, [onChange]);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        value={filters.type?.[0] ?? 'all'}
        onValueChange={handleTypeChange}
      >
        <SelectTrigger className="w-full sm:w-[160px]" aria-label="Filter by type">
          <SelectValue placeholder="All Types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          {NODE_TYPES.map((t) => (
            <SelectItem key={t} value={t}>
              {t.replace(/_/g, ' ')}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.kind ?? 'all'}
        onValueChange={handleKindChange}
      >
        <SelectTrigger className="w-full sm:w-[130px]" aria-label="Filter by kind">
          <SelectValue placeholder="All Kinds" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Kinds</SelectItem>
          {KINDS.map((k) => (
            <SelectItem key={k} value={k}>
              {k}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
        <Checkbox
          checked={filters.pinned === true}
          onCheckedChange={handlePinnedChange}
          aria-label="Show pinned only"
        />
        Pinned only
      </label>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="gap-1 text-muted-foreground"
        >
          <FilterX className="h-3.5 w-3.5" />
          Clear
        </Button>
      )}
    </div>
  );
}
