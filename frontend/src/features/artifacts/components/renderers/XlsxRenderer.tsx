'use client';

import * as React from 'react';
import * as XLSX from 'xlsx';
import { cn } from '@/lib/utils';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { DownloadFallback } from './DownloadFallback';

interface XlsxRendererProps {
  content: ArrayBuffer;
  filename: string;
  signedUrl: string;
}

interface SheetData {
  headers: string[];
  rows: string[][];
  totalRows: number;
  truncated: boolean;
}

const MAX_ROWS = 500;

function highlightCell(value: string, term: string): React.ReactNode {
  if (!term) return value;
  const idx = value.toLowerCase().indexOf(term.toLowerCase());
  if (idx === -1) return value;
  return (
    <>
      {value.slice(0, idx)}
      <mark className="bg-primary/20 rounded-sm px-0.5">{value.slice(idx, idx + term.length)}</mark>
      {value.slice(idx + term.length)}
    </>
  );
}

export function XlsxRenderer({ content, filename, signedUrl }: XlsxRendererProps) {
  const [parsedWorkbook, setParsedWorkbook] = React.useState<XLSX.WorkBook | null>(null);
  const [isParsing, setIsParsing] = React.useState(true);
  const [activeSheet, setActiveSheet] = React.useState<string>('');
  const [error, setError] = React.useState(false);
  const [searchInput, setSearchInput] = React.useState('');
  const [searchTerm, setSearchTerm] = React.useState('');
  const [colWidths, setColWidths] = React.useState<Record<number, number>>({});
  const dragState = React.useRef<{ colIndex: number; startX: number; startWidth: number } | null>(
    null
  );

  React.useEffect(() => {
    setIsParsing(true);
    setError(false);
    setParsedWorkbook(null);
    setActiveSheet('');

    const timeoutId = setTimeout(() => {
      try {
        const wb = XLSX.read(content, { dense: true });
        setParsedWorkbook(wb);
        setActiveSheet(wb.SheetNames[0] ?? '');
      } catch {
        setError(true);
      } finally {
        setIsParsing(false);
      }
    }, 0);

    return () => clearTimeout(timeoutId);
  }, [content]);

  // Clear search when active sheet changes
  React.useEffect(() => {
    setSearchInput('');
    setSearchTerm('');
    setColWidths({});
  }, [activeSheet]);

  // Debounce search input at 300ms
  React.useEffect(() => {
    const timer = setTimeout(() => setSearchTerm(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const sheetData = React.useMemo<SheetData | null>(() => {
    if (!parsedWorkbook || !activeSheet) return null;
    const ws = parsedWorkbook.Sheets[activeSheet];
    if (!ws || !ws['!ref']) return null;

    // Decode full range to get total row count BEFORE conversion
    const fullRange = XLSX.utils.decode_range(ws['!ref']);
    const totalRows = Math.max(0, fullRange.e.r); // row 0 is header, data rows start at 1
    const truncated = totalRows > MAX_ROWS;

    // Limit conversion range to header + MAX_ROWS to avoid memory spikes on large sheets
    const limitedRange = truncated
      ? { s: fullRange.s, e: { ...fullRange.e, r: MAX_ROWS } }
      : fullRange;

    const jsonRows = XLSX.utils.sheet_to_json<unknown[]>(ws, {
      header: 1,
      raw: false,
      defval: '',
      range: limitedRange,
    });
    const [headerRow, ...dataRows] = jsonRows;
    return {
      headers: (headerRow ?? []) as string[],
      rows: dataRows as string[][],
      totalRows,
      truncated,
    };
  }, [parsedWorkbook, activeSheet]);

  const matchCount = React.useMemo(() => {
    if (!searchTerm || !sheetData) return 0;
    const term = searchTerm.toLowerCase();
    let count = 0;
    for (const row of sheetData.rows) {
      for (const cell of row) {
        if (String(cell).toLowerCase().includes(term)) count++;
      }
    }
    for (const h of sheetData.headers) {
      if (String(h).toLowerCase().includes(term)) count++;
    }
    return count;
  }, [searchTerm, sheetData]);

  // Column resize drag handlers
  const handleResizeMouseDown = React.useCallback((e: React.MouseEvent, colIndex: number) => {
    e.preventDefault();
    const th = (e.currentTarget as HTMLElement).closest('th');
    const startWidth = th ? th.getBoundingClientRect().width : 120;
    dragState.current = { colIndex, startX: e.clientX, startWidth };

    const onMouseMove = (moveEvent: MouseEvent) => {
      const currentDrag = dragState.current;
      if (!currentDrag) return;
      const delta = moveEvent.clientX - currentDrag.startX;
      const newWidth = Math.max(60, currentDrag.startWidth + delta);
      const { colIndex: dragColIndex } = currentDrag;
      setColWidths((prev) => ({ ...prev, [dragColIndex]: newWidth }));
    };

    const onMouseUp = () => {
      dragState.current = null;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  if (isParsing) {
    return (
      <div
        className="flex items-center justify-center p-8"
        role="status"
        aria-label="Parsing spreadsheet"
      >
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  if (error || !sheetData) {
    return <DownloadFallback filename={filename} signedUrl={signedUrl} reason="error" />;
  }

  return (
    <div className="flex flex-col h-full">
      {sheetData.truncated && (
        <p className="text-xs text-muted-foreground px-4 py-1.5 border-b border-amber-200/50 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800/30 shrink-0">
          Showing 500 of {sheetData.totalRows.toLocaleString()} rows. Download for full data.
        </p>
      )}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/60 shrink-0 bg-muted/20">
        <Input
          placeholder="Search in sheet..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="h-7 max-w-[240px] text-xs bg-background"
          aria-label="Search in sheet"
        />
        {searchTerm && (
          <span className="text-[11px] text-muted-foreground whitespace-nowrap tabular-nums">
            {matchCount} {matchCount === 1 ? 'match' : 'matches'}
          </span>
        )}
      </div>
      <ScrollArea className="flex-1">
        <Table className="table-fixed">
          <TableHeader className="sticky top-0 z-10 bg-muted/80 backdrop-blur-sm shadow-[0_1px_3px_0_rgb(0_0_0/0.05)]">
            <TableRow className="border-b-2 border-border/60">
              {sheetData.headers.map((h, i) => (
                <TableHead
                  key={i}
                  className="relative overflow-hidden"
                  style={{ width: colWidths[i] ?? 120, minWidth: 60 }}
                >
                  {highlightCell(String(h), searchTerm)}
                  <div
                    role="separator"
                    aria-label={`Resize column ${i + 1}`}
                    aria-orientation="vertical"
                    tabIndex={0}
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/30 focus:bg-primary/40 select-none"
                    onMouseDown={(e) => handleResizeMouseDown(e, i)}
                    onKeyDown={(e) => {
                      const step = e.shiftKey ? 20 : 5;
                      if (e.key === 'ArrowRight') {
                        e.preventDefault();
                        setColWidths((prev) => ({
                          ...prev,
                          [i]: Math.max(60, (prev[i] ?? 120) + step),
                        }));
                      } else if (e.key === 'ArrowLeft') {
                        e.preventDefault();
                        setColWidths((prev) => ({
                          ...prev,
                          [i]: Math.max(60, (prev[i] ?? 120) - step),
                        }));
                      }
                    }}
                  />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sheetData.rows.map((row, ri) => (
              <TableRow key={ri} className={ri % 2 !== 0 ? 'bg-muted/30' : undefined}>
                {row.map((cell, ci) => (
                  <TableCell
                    key={ci}
                    style={{ width: colWidths[ci] ?? 120, minWidth: 60 }}
                    className="overflow-hidden text-ellipsis"
                  >
                    {highlightCell(String(cell), searchTerm)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
      {parsedWorkbook && parsedWorkbook.SheetNames.length > 1 && (
        <div className="flex items-center gap-0.5 px-2 py-1.5 border-t border-border/60 overflow-x-auto shrink-0 bg-muted/30">
          {parsedWorkbook.SheetNames.map((name) => (
            <button
              key={name}
              onClick={() => setActiveSheet(name)}
              className={cn(
                'px-3 py-1 text-xs rounded-md whitespace-nowrap transition-all duration-150',
                activeSheet === name
                  ? 'bg-background text-foreground font-medium shadow-sm ring-1 ring-border/50'
                  : 'text-muted-foreground hover:text-foreground hover:bg-background/60'
              )}
            >
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
