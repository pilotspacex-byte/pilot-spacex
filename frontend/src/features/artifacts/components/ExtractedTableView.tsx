'use client';

/**
 * ExtractedTableView - Sortable, copyable interactive markdown table.
 *
 * Parses a markdown table string from the extraction result and renders it
 * as a shadcn/ui Table with sort headers and a "Copy as Markdown" button.
 *
 * Feature 044: Artifact UI Enhancements (AUI-03)
 */
import * as React from 'react';
import { Copy, Check, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type SortConfig = { colIndex: number; dir: 'asc' | 'desc' } | null;

/**
 * Parse a markdown table string into headers and data rows.
 * Returns { headers: string[], rows: string[][] } or null if not a valid table.
 *
 * Handles the standard markdown table format:
 *   | Col1 | Col2 |
 *   |------|------|
 *   | val1 | val2 |
 */
function parseMarkdownTable(markdown: string): { headers: string[]; rows: string[][] } | null {
  const lines = markdown.trim().split('\n').filter(Boolean);
  if (lines.length < 3) return null;

  const parseRow = (line: string): string[] =>
    line
      .split('|')
      .slice(1, -1)
      .map((cell) => cell.trim());

  const isSeparatorRow = (line: string) => /^\s*\|[\s|:-]+\|\s*$/.test(line);

  if (!isSeparatorRow(lines[1]!)) return null;

  const headers = parseRow(lines[0]!);
  const rows = lines.slice(2).map(parseRow);

  if (headers.length === 0 || rows.length === 0) return null;
  return { headers, rows };
}

function SortIcon({ colIndex, sort }: { colIndex: number; sort: SortConfig }) {
  if (!sort || sort.colIndex !== colIndex) return <ArrowUpDown className="size-3 opacity-40" />;
  return sort.dir === 'asc' ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />;
}

export interface ExtractedTableViewProps {
  /** Raw markdown table string from extraction.tables[] */
  markdown: string;
  className?: string;
}

export function ExtractedTableView({ markdown, className }: ExtractedTableViewProps) {
  const [sort, setSort] = React.useState<SortConfig>(null);
  const [copied, setCopied] = React.useState(false);

  const parsed = React.useMemo(() => parseMarkdownTable(markdown), [markdown]);

  const sortedRows = React.useMemo(() => {
    if (!parsed) return [];
    if (!sort) return parsed.rows;
    // Always spread to avoid mutating cached TanStack Query data
    return [...parsed.rows].sort((a, b) => {
      const cmp = (a[sort.colIndex] ?? '').localeCompare(b[sort.colIndex] ?? '');
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [parsed, sort]);

  const handleSort = (colIndex: number) => {
    setSort((prev) => {
      if (!prev || prev.colIndex !== colIndex) return { colIndex, dir: 'asc' };
      if (prev.dir === 'asc') return { colIndex, dir: 'desc' };
      return null; // third click clears sort
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available (e.g., test environment) - fail silently
    }
  };

  if (!parsed) {
    return (
      <div className={cn('text-xs text-muted-foreground italic px-2 py-1', className)}>
        (Could not parse table)
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="text-xs text-muted-foreground">{parsed.rows.length} rows</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-2 text-xs"
          onClick={handleCopy}
          aria-label="Copy table as Markdown"
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          {copied ? 'Copied' : 'Copy as Markdown'}
        </Button>
      </div>
      <div className="overflow-x-auto rounded border">
        <Table>
          <TableHeader>
            <TableRow>
              {parsed.headers.map((header, i) => (
                <TableHead
                  key={i}
                  className="cursor-pointer select-none whitespace-nowrap"
                  onClick={() => handleSort(i)}
                >
                  <span className="inline-flex items-center gap-1">
                    {header}
                    <SortIcon colIndex={i} sort={sort} />
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedRows.map((row, ri) => (
              <TableRow key={ri}>
                {row.map((cell, ci) => (
                  <TableCell key={ci} className="whitespace-nowrap">
                    {cell}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
