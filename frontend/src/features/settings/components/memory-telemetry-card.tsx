/**
 * MemoryTelemetryCard — displays hit-rate, p95 latency, and producer counters.
 *
 * Phase 70 Wave 4. Refreshes on 30s interval via TanStack Query refetchInterval.
 *
 * Plain React component — NOT observer().
 */

'use client';

import { Activity, Gauge } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAITelemetry } from '../hooks/use-ai-telemetry';

interface MemoryTelemetryCardProps {
  workspaceId: string | undefined;
}

export function MemoryTelemetryCard({ workspaceId }: MemoryTelemetryCardProps) {
  const { data, isLoading } = useAITelemetry(workspaceId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Memory Telemetry</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const { memory, producers } = data;
  const hitRatePercent = (memory.hit_rate * 100).toFixed(1);

  // Collect producer names from enqueued keys
  const producerNames = Object.keys(producers.enqueued);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">Memory Telemetry</CardTitle>
        </div>
        <CardDescription>
          Real-time recall performance and producer throughput. Refreshes every 30 seconds.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Gauge className="h-3 w-3" />
              Hit Rate
            </p>
            <p className="text-2xl font-semibold tabular-nums">{hitRatePercent}%</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Recall p95</p>
            <p className="text-2xl font-semibold tabular-nums">{memory.recall_p95_ms.toFixed(1)}ms</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Total Recalls</p>
            <p className="text-2xl font-semibold tabular-nums">
              {memory.total_recalls.toLocaleString()}
            </p>
          </div>
        </div>

        {/* Producer counters table */}
        {producerNames.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Producer</TableHead>
                <TableHead className="text-right">Enqueued</TableHead>
                <TableHead className="text-right">Dropped</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {producerNames.map((name) => {
                const enqueued = producers.enqueued[name] ?? 0;
                // Sum all dropped reasons for this producer
                const dropped = Object.entries(producers.dropped)
                  .filter(([key]) => key.startsWith(`${name}::`))
                  .reduce((sum, [, count]) => sum + count, 0);
                return (
                  <TableRow key={name}>
                    <TableCell className="font-medium text-sm">
                      {name.replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{enqueued}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {dropped > 0 ? (
                        <span className="text-destructive">{dropped}</span>
                      ) : (
                        '0'
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
