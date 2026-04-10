/**
 * MemorySearchBar — Debounced search input for semantic memory search.
 *
 * Phase 71: 300ms debounce, Search icon, clear button.
 */

'use client';

import * as React from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface MemorySearchBarProps {
  value: string;
  onChange: (q: string) => void;
}

export function MemorySearchBar({ value, onChange }: MemorySearchBarProps) {
  const [local, setLocal] = React.useState(value);
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external value changes (e.g. clear filters)
  React.useEffect(() => {
    setLocal(value);
  }, [value]);

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const next = e.target.value;
      setLocal(next);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => onChange(next), 300);
    },
    [onChange],
  );

  const handleClear = React.useCallback(() => {
    setLocal('');
    onChange('');
    if (timerRef.current) clearTimeout(timerRef.current);
  }, [onChange]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div className="relative flex-1 min-w-[200px]">
      <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
      <Input
        role="searchbox"
        aria-label="Search memories"
        aria-describedby="memory-search-results"
        placeholder="Search memories semantically..."
        value={local}
        onChange={handleChange}
        className="pl-8 pr-8"
      />
      {local && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-0.5 text-muted-foreground hover:text-foreground transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
