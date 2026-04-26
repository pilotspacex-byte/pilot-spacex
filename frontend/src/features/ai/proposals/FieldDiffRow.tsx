/**
 * FieldDiffRow — semantic per-field row for a fields-diff proposal payload.
 * Renders:  <label>:  [before-chip] → [after-chip]
 * UI-SPEC §5.
 */

import { memo } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FieldDiffRowPayload } from './types';

interface FieldDiffRowProps {
  row: FieldDiffRowPayload;
  className?: string;
}

const VALUE_TRUNCATE_AT = 80;

function stringifyValue(v: unknown): string {
  if (v === null || v === undefined) return '∅';
  if (typeof v === 'string') return v;
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    const s = JSON.stringify(v);
    return s.length > VALUE_TRUNCATE_AT ? `${s.slice(0, VALUE_TRUNCATE_AT - 1)}…` : s;
  } catch {
    return String(v);
  }
}

export const FieldDiffRow = memo<FieldDiffRowProps>(function FieldDiffRow({ row, className }) {
  const before = stringifyValue(row.before);
  const after = stringifyValue(row.after);

  return (
    <div
      role="group"
      aria-label={`${row.label} changed from ${before} to ${after}`}
      className={cn('flex items-center gap-2 py-1.5 flex-wrap', className)}
      data-testid="field-diff-row"
      data-field={row.field}
    >
      <span className="text-xs font-medium text-foreground shrink-0">{row.label}:</span>
      <del
        role="deletion"
        data-testid="field-diff-before"
        className={cn(
          'inline-flex items-center rounded-md px-2 py-0.5 no-underline',
          'text-xs font-medium leading-none',
          'bg-[#fecaca] text-[#dc2626]'
        )}
      >
        {before}
      </del>
      <ArrowRight aria-hidden="true" className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <ins
        role="insertion"
        data-testid="field-diff-after"
        className={cn(
          'inline-flex items-center rounded-md px-2 py-0.5 no-underline',
          'text-xs font-medium leading-none',
          'bg-[#bbf7d0] text-[#16a34a]'
        )}
      >
        {after}
      </ins>
    </div>
  );
});

FieldDiffRow.displayName = 'FieldDiffRow';
