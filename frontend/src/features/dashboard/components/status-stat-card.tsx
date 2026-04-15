'use client';

/**
 * StatusStatCard — Stat card for queued/running/done/failed issue counts.
 *
 * Uses a color-coded left border (3px) driven by a CSS variable color token.
 * Read-only display — no click action.
 *
 * Phase 77 — Implementation Dashboard (DSH-01, UIX-04)
 */
import * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface StatusStatCardProps {
  label: string;
  count: number;
  /** CSS variable token, e.g. "--info", "--primary", "--destructive", "--state-in-progress" */
  colorToken: string;
  className?: string;
}

export const StatusStatCard = React.memo(function StatusStatCard({
  label,
  count,
  colorToken,
  className,
}: StatusStatCardProps) {
  return (
    <Card
      className={cn('border-l-[3px] rounded-lg shadow-none', className)}
      style={{ borderLeftColor: `hsl(var(${colorToken}))` }}
      aria-label={`${count} ${label} issues`}
    >
      <CardContent className="p-4">
        <p
          className="text-[20px] font-semibold leading-tight text-foreground"
          aria-hidden="true"
        >
          {count}
        </p>
        <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide mt-0.5">
          {label}
        </p>
      </CardContent>
    </Card>
  );
});

StatusStatCard.displayName = 'StatusStatCard';
