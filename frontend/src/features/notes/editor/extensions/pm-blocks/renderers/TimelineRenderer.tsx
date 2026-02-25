'use client';

import { useCallback, useMemo } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn, generateUUID } from '@/lib/utils';
import type { PMRendererProps } from '../PMBlockNodeView';
import { pmBlockStyles } from '../pm-block-styles';

interface Milestone {
  id: string;
  name: string;
  date: string;
  status: 'on-track' | 'at-risk' | 'blocked';
  dependencies: string[];
}

interface TimelineData {
  title: string;
  milestones: Milestone[];
}

const STATUS_LABELS: Record<Milestone['status'], string> = {
  'on-track': 'On Track',
  'at-risk': 'At Risk',
  blocked: 'Blocked',
};

const STATUS_CYCLE: Milestone['status'][] = ['on-track', 'at-risk', 'blocked'];

const STATUS_DOT_COLORS: Record<Milestone['status'], string> = {
  'on-track': 'bg-primary',
  'at-risk': 'bg-[#D9853F]',
  blocked: 'bg-destructive',
};

const STATUS_TEXT_COLORS: Record<Milestone['status'], string> = {
  'on-track': 'text-primary',
  'at-risk': 'text-[#D9853F]',
  blocked: 'text-destructive',
};

export function TimelineRenderer({ data, readOnly, onDataChange }: PMRendererProps) {
  const parsed = useMemo<TimelineData>(() => {
    const d = data as unknown as TimelineData;
    return {
      title: d.title || 'Project Timeline',
      milestones: Array.isArray(d.milestones) ? d.milestones : [],
    };
  }, [data]);

  const updateTitle = useCallback(
    (title: string) => {
      if (readOnly) return;
      onDataChange({ ...parsed, title } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const updateMilestone = useCallback(
    (id: string, updates: Partial<Milestone>) => {
      if (readOnly) return;
      const milestones = parsed.milestones.map((m) => (m.id === id ? { ...m, ...updates } : m));
      onDataChange({ ...parsed, milestones } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const addMilestone = useCallback(() => {
    if (readOnly) return;
    const id = `m-${generateUUID()}`;
    const milestones = [
      ...parsed.milestones,
      { id, name: '', date: '', status: 'on-track' as const, dependencies: [] },
    ];
    onDataChange({ ...parsed, milestones } as unknown as Record<string, unknown>);
  }, [parsed, readOnly, onDataChange]);

  const removeMilestone = useCallback(
    (id: string) => {
      if (readOnly) return;
      const milestones = parsed.milestones.filter((m) => m.id !== id);
      onDataChange({ ...parsed, milestones } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const cycleStatus = useCallback(
    (id: string) => {
      if (readOnly) return;
      const m = parsed.milestones.find((ms) => ms.id === id);
      if (!m) return;
      const idx = STATUS_CYCLE.indexOf(m.status);
      const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
      updateMilestone(id, { status: next });
    },
    [parsed.milestones, readOnly, updateMilestone]
  );

  const sorted = useMemo(
    () =>
      [...parsed.milestones].sort((a, b) => {
        if (!a.date && !b.date) return 0;
        if (!a.date) return 1;
        if (!b.date) return -1;
        return a.date.localeCompare(b.date);
      }),
    [parsed.milestones]
  );

  return (
    <div className={pmBlockStyles.shared.container}>
      {/* Header */}
      <div className={pmBlockStyles.shared.header}>
        {readOnly ? (
          <h3 className={pmBlockStyles.shared.title}>{parsed.title}</h3>
        ) : (
          <input
            className={pmBlockStyles.shared.titleInput}
            value={parsed.title}
            onChange={(e) => updateTitle(e.target.value)}
            placeholder="Timeline title"
            aria-label="Timeline title"
          />
        )}
      </div>

      {/* Timeline visual */}
      <div className={pmBlockStyles.timeline.svgContainer}>
        {sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground py-2">No milestones yet.</p>
        ) : (
          <div className="flex items-start gap-0 min-w-max">
            {sorted.map((ms, idx) => (
              <div key={ms.id} className="flex items-start">
                {/* Milestone card */}
                <div
                  className={`${pmBlockStyles.timeline.milestone} min-w-[140px] min-h-[44px] p-2`}
                  role="button"
                  tabIndex={readOnly ? -1 : 0}
                  aria-label={`${ms.name || 'Unnamed'}: ${STATUS_LABELS[ms.status]}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      cycleStatus(ms.id);
                    }
                  }}
                  onClick={() => cycleStatus(ms.id)}
                >
                  {/* Status dot */}
                  <div
                    className={`w-3 h-3 rounded-full ${STATUS_DOT_COLORS[ms.status]} shrink-0`}
                    title={STATUS_LABELS[ms.status]}
                  />

                  {/* Name */}
                  {readOnly ? (
                    <span className={cn('text-xs font-medium', STATUS_TEXT_COLORS[ms.status])}>
                      {ms.name || 'Unnamed'}
                    </span>
                  ) : (
                    <input
                      className="text-xs font-medium bg-transparent border-none outline-none w-full text-center"
                      value={ms.name}
                      onChange={(e) => updateMilestone(ms.id, { name: e.target.value })}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                      placeholder="Milestone name"
                      aria-label="Milestone name"
                    />
                  )}

                  {/* Date */}
                  {readOnly ? (
                    <span className="text-[10px] text-muted-foreground">{ms.date || '—'}</span>
                  ) : (
                    <input
                      type="date"
                      className="text-[10px] bg-transparent border-none outline-none text-muted-foreground"
                      value={ms.date}
                      onChange={(e) => updateMilestone(ms.id, { date: e.target.value })}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                      aria-label="Milestone date"
                    />
                  )}

                  {/* Status label */}
                  <span className={cn('text-[10px]', STATUS_TEXT_COLORS[ms.status])}>
                    {STATUS_LABELS[ms.status]}
                  </span>

                  {/* Remove button */}
                  {!readOnly && (
                    <button
                      type="button"
                      className="text-[10px] text-muted-foreground hover:text-destructive mt-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeMilestone(ms.id);
                      }}
                      aria-label={`Remove ${ms.name || 'milestone'}`}
                    >
                      Remove
                    </button>
                  )}
                </div>

                {/* Connector line */}
                {idx < sorted.length - 1 && (
                  <div className="flex items-center self-center pt-1">
                    <div className="w-8 h-px bg-border" />
                    <ChevronRight className="size-3 text-border" />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add milestone */}
      {!readOnly && (
        <button
          type="button"
          className={pmBlockStyles.shared.addButton}
          onClick={addMilestone}
          aria-label="Add milestone"
        >
          + Add Milestone
        </button>
      )}

      {/* Summary */}
      {sorted.length > 0 && (
        <div className="flex gap-3 text-[10px] text-muted-foreground mt-2 pt-2 border-t border-border">
          <span>{sorted.filter((m) => m.status === 'on-track').length} on track</span>
          <span>{sorted.filter((m) => m.status === 'at-risk').length} at risk</span>
          <span>{sorted.filter((m) => m.status === 'blocked').length} blocked</span>
        </div>
      )}
    </div>
  );
}
