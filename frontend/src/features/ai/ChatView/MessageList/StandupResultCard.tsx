/**
 * StandupResultCard - Renders daily standup structured results.
 *
 * Extracted from StructuredResultCard to keep file under 700 lines.
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import { CalendarCheck, Copy, Check } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface StandupItem {
  identifier: string;
  title: string;
  reason?: string;
}

interface StandupResultData {
  yesterday: StandupItem[];
  today: StandupItem[];
  blockers: StandupItem[];
  period: string;
}

/** Format standup data as clean markdown text for Slack/clipboard. */
export function formatStandupForClipboard(data: StandupResultData): string {
  const lines: string[] = [];

  lines.push(`**Daily Standup** — ${data.period}`);
  lines.push('');

  lines.push('**Yesterday (Completed)**');
  if (data.yesterday.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.yesterday) {
      lines.push(`- ${item.identifier}: ${item.title}`);
    }
  }
  lines.push('');

  lines.push('**Today (In Progress)**');
  if (data.today.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.today) {
      lines.push(`- ${item.identifier}: ${item.title}`);
    }
  }
  lines.push('');

  lines.push('**Blockers**');
  if (data.blockers.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.blockers) {
      const suffix = item.reason ? ` — ${item.reason}` : '';
      lines.push(`- ${item.identifier}: ${item.title}${suffix}`);
    }
  }

  return lines.join('\n');
}

function StandupSection({
  heading,
  items,
  accentClass,
  showReason,
}: {
  heading: string;
  items: StandupItem[];
  accentClass: string;
  showReason?: boolean;
}) {
  return (
    <div>
      <h4 className={cn('text-xs font-semibold uppercase tracking-wider mb-2', accentClass)}>
        {heading}
      </h4>
      {items.length === 0 ? (
        <p className="text-xs italic text-muted-foreground">(No items)</p>
      ) : (
        <ul className="space-y-1.5" role="list">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm">
              <span
                className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current opacity-40"
                aria-hidden="true"
              />
              <span>
                <code className="font-mono text-xs text-primary">{item.identifier}</code>{' '}
                <span className="text-foreground">{item.title}</span>
                {showReason && item.reason && (
                  <span className="text-xs text-muted-foreground"> — {item.reason}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function isStandupItemArray(value: unknown): value is StandupItem[] {
  return (
    Array.isArray(value) &&
    value.every((item) => typeof item === 'object' && item !== null && 'title' in item)
  );
}

export function StandupResultCard({ data }: { data: Record<string, unknown> }) {
  const yesterday = useMemo(
    () => (isStandupItemArray(data.yesterday) ? data.yesterday : []),
    [data.yesterday]
  );
  const today = useMemo(() => (isStandupItemArray(data.today) ? data.today : []), [data.today]);
  const blockers = useMemo(
    () => (isStandupItemArray(data.blockers) ? data.blockers : []),
    [data.blockers]
  );
  const period = typeof data.period === 'string' ? data.period : '';

  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = formatStandupForClipboard({ yesterday, today, blockers, period });
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        toast.error('Could not copy to clipboard');
      });
  }, [yesterday, today, blockers, period]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarCheck className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-medium">Daily Standup</span>
          {period && <span className="text-xs text-muted-foreground">{period}</span>}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? 'Copied to clipboard' : 'Copy standup to clipboard'}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium',
            'transition-colors duration-150',
            'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            copied ? 'text-primary' : 'text-muted-foreground'
          )}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" aria-hidden="true" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" aria-hidden="true" />
              Copy
            </>
          )}
        </button>
      </div>

      <StandupSection
        heading="Yesterday (Completed)"
        items={yesterday}
        accentClass="text-muted-foreground"
      />
      <StandupSection heading="Today (In Progress)" items={today} accentClass="text-primary" />
      <StandupSection
        heading="Blockers"
        items={blockers}
        accentClass="text-[var(--warning)]"
        showReason
      />
    </div>
  );
}
