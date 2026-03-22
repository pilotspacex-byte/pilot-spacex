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
import { DownloadFallback } from './DownloadFallback';

interface XlsxRendererProps {
  content: ArrayBuffer;
}

interface SheetData {
  headers: string[];
  rows: string[][];
  totalRows: number;
  truncated: boolean;
}

const MAX_ROWS = 500;

export function XlsxRenderer({ content }: XlsxRendererProps) {
  const [parsedWorkbook, setParsedWorkbook] = React.useState<XLSX.WorkBook | null>(null);
  const [isParsing, setIsParsing] = React.useState(true);
  const [activeSheet, setActiveSheet] = React.useState<string>('');
  const [error, setError] = React.useState(false);

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

  const sheetData = React.useMemo<SheetData | null>(() => {
    if (!parsedWorkbook || !activeSheet) return null;
    const ws = parsedWorkbook.Sheets[activeSheet];
    if (!ws) return null;
    const jsonRows = XLSX.utils.sheet_to_json<unknown[]>(ws, {
      header: 1,
      raw: false,
      defval: '',
    });
    const [headerRow, ...dataRows] = jsonRows;
    const totalRows = dataRows.length;
    const truncated = totalRows > MAX_ROWS;
    return {
      headers: (headerRow ?? []) as string[],
      rows: dataRows.slice(0, MAX_ROWS) as string[][],
      totalRows,
      truncated,
    };
  }, [parsedWorkbook, activeSheet]);

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
    return <DownloadFallback filename="spreadsheet.xlsx" signedUrl="" reason="error" />;
  }

  return (
    <div className="flex flex-col h-full">
      {sheetData.truncated && (
        <p className="text-xs text-muted-foreground px-4 py-2 border-b shrink-0">
          Showing 500 of {sheetData.totalRows.toLocaleString()} rows. Download for full data.
        </p>
      )}
      <ScrollArea className="flex-1">
        <Table>
          <TableHeader>
            <TableRow>
              {sheetData.headers.map((h, i) => (
                <TableHead key={i}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {sheetData.rows.map((row, ri) => (
              <TableRow key={ri} className={ri % 2 !== 0 ? 'bg-muted/30' : undefined}>
                {row.map((cell, ci) => (
                  <TableCell key={ci}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
      {parsedWorkbook && parsedWorkbook.SheetNames.length > 1 && (
        <div className="flex items-center gap-1 px-3 py-2 border-t overflow-x-auto shrink-0">
          {parsedWorkbook.SheetNames.map((name) => (
            <button
              key={name}
              onClick={() => setActiveSheet(name)}
              className={cn(
                'px-3 py-1 text-xs rounded-md whitespace-nowrap transition-colors',
                activeSheet === name
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
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
