'use client';

import * as React from 'react';
import Papa from 'papaparse';
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

interface CsvRendererProps {
  content: string;
}

interface ParsedCSV {
  headers: string[];
  rows: string[][];
  totalRows: number;
  truncated: boolean;
}

const MAX_ROWS = 500;

export function CsvRenderer({ content }: CsvRendererProps) {
  const parseResult = React.useMemo<{ parsed: ParsedCSV } | { error: true }>(() => {
    try {
      const result = Papa.parse<string[]>(content, {
        header: false,
        skipEmptyLines: true,
      });
      const allRows = result.data as string[][];
      const [headerRow, ...dataRows] = allRows;
      const truncated = dataRows.length > MAX_ROWS;
      return {
        parsed: {
          headers: headerRow ?? [],
          rows: dataRows.slice(0, MAX_ROWS),
          totalRows: dataRows.length,
          truncated,
        },
      };
    } catch {
      return { error: true as const };
    }
  }, [content]);

  if ('error' in parseResult) {
    return <DownloadFallback filename="data.csv" signedUrl="" reason="error" />;
  }

  const { parsed } = parseResult;

  return (
    <div className="flex flex-col h-full">
      {parsed.truncated && (
        <p className="text-xs text-muted-foreground px-4 py-2 border-b shrink-0">
          Showing 500 of {parsed.totalRows.toLocaleString()} rows. Download for full data.
        </p>
      )}
      <ScrollArea className="flex-1">
        <Table>
          <TableHeader>
            <TableRow>
              {parsed.headers.map((h, i) => (
                <TableHead key={i}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {parsed.rows.map((row, ri) => (
              <TableRow key={ri} className={ri % 2 !== 0 ? 'bg-muted/30' : undefined}>
                {row.map((cell, ci) => (
                  <TableCell key={ci}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}
