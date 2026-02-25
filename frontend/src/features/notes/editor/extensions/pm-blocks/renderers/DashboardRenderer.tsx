'use client';

import { useCallback, useMemo } from 'react';
import { generateUUID } from '@/lib/utils';
import type { PMRendererProps } from '../PMBlockNodeView';
import { pmBlockStyles } from '../pm-block-styles';

interface Widget {
  id: string;
  metric: string;
  value: number;
  trend: 'up' | 'down' | 'flat';
  unit: string;
  target?: number;
}

interface DashboardData {
  title: string;
  widgets: Widget[];
}

const TREND_ICONS: Record<Widget['trend'], string> = {
  up: '\u2191', // ↑
  down: '\u2193', // ↓
  flat: '\u2192', // →
};

const TREND_STYLES: Record<Widget['trend'], string> = {
  up: pmBlockStyles.dashboard.trendUp,
  down: pmBlockStyles.dashboard.trendDown,
  flat: pmBlockStyles.dashboard.trendFlat,
};

const TREND_CYCLE: Widget['trend'][] = ['flat', 'up', 'down'];

export function DashboardRenderer({ data, readOnly, onDataChange }: PMRendererProps) {
  const parsed = useMemo<DashboardData>(() => {
    const d = data as unknown as DashboardData;
    return {
      title: d.title || 'KPI Dashboard',
      widgets: Array.isArray(d.widgets) ? d.widgets : [],
    };
  }, [data]);

  const updateTitle = useCallback(
    (title: string) => {
      if (readOnly) return;
      onDataChange({ ...parsed, title } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const updateWidget = useCallback(
    (id: string, updates: Partial<Widget>) => {
      if (readOnly) return;
      const widgets = parsed.widgets.map((w) => (w.id === id ? { ...w, ...updates } : w));
      onDataChange({ ...parsed, widgets } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const addWidget = useCallback(() => {
    if (readOnly) return;
    const id = `w-${generateUUID()}`;
    const widgets = [
      ...parsed.widgets,
      { id, metric: '', value: 0, trend: 'flat' as const, unit: '' },
    ];
    onDataChange({ ...parsed, widgets } as unknown as Record<string, unknown>);
  }, [parsed, readOnly, onDataChange]);

  const removeWidget = useCallback(
    (id: string) => {
      if (readOnly) return;
      const widgets = parsed.widgets.filter((w) => w.id !== id);
      onDataChange({ ...parsed, widgets } as unknown as Record<string, unknown>);
    },
    [parsed, readOnly, onDataChange]
  );

  const cycleTrend = useCallback(
    (id: string) => {
      if (readOnly) return;
      const w = parsed.widgets.find((wg) => wg.id === id);
      if (!w) return;
      const idx = TREND_CYCLE.indexOf(w.trend);
      const next = TREND_CYCLE[(idx + 1) % TREND_CYCLE.length];
      updateWidget(id, { trend: next });
    },
    [parsed.widgets, readOnly, updateWidget]
  );

  const formatValue = (value: number, unit: string) => {
    if (unit === '%') return `${value}%`;
    if (unit === '$') return `$${value.toLocaleString()}`;
    return unit ? `${value.toLocaleString()} ${unit}` : value.toLocaleString();
  };

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
            placeholder="Dashboard title"
            aria-label="Dashboard title"
          />
        )}
      </div>

      {/* Widget grid */}
      {parsed.widgets.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2">No widgets yet.</p>
      ) : (
        <div className={pmBlockStyles.dashboard.widgetGrid}>
          {parsed.widgets.map((widget) => (
            <div key={widget.id} className={pmBlockStyles.dashboard.widget}>
              {/* Metric name */}
              {readOnly ? (
                <div className={pmBlockStyles.dashboard.widgetTitle}>
                  {widget.metric || 'Unnamed Metric'}
                </div>
              ) : (
                <input
                  className={`${pmBlockStyles.dashboard.widgetTitle} bg-transparent border-none outline-none w-full`}
                  value={widget.metric}
                  onChange={(e) => updateWidget(widget.id, { metric: e.target.value })}
                  placeholder="Metric name"
                  aria-label="Metric name"
                />
              )}

              {/* Value */}
              <div className="flex items-baseline gap-2">
                {readOnly ? (
                  <span className={pmBlockStyles.dashboard.widgetValue}>
                    {formatValue(widget.value, widget.unit)}
                  </span>
                ) : (
                  <div className="flex items-baseline gap-1">
                    <input
                      type="number"
                      className={`${pmBlockStyles.dashboard.widgetValue} bg-transparent border-none outline-none w-24`}
                      value={widget.value}
                      onChange={(e) => updateWidget(widget.id, { value: Number(e.target.value) })}
                      aria-label="Metric value"
                    />
                    <input
                      className="text-xs bg-transparent border-none outline-none w-10 text-muted-foreground"
                      value={widget.unit}
                      onChange={(e) => updateWidget(widget.id, { unit: e.target.value })}
                      placeholder="unit"
                      aria-label="Metric unit"
                    />
                  </div>
                )}

                {/* Trend indicator */}
                <button
                  type="button"
                  className={TREND_STYLES[widget.trend]}
                  onClick={() => cycleTrend(widget.id)}
                  disabled={readOnly}
                  aria-label={`Trend: ${widget.trend}. Click to cycle.`}
                  tabIndex={readOnly ? -1 : 0}
                >
                  <span aria-hidden="true">{TREND_ICONS[widget.trend]}</span> {widget.trend}
                </button>
              </div>

              {/* Target (optional) */}
              {!readOnly && (
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[10px] text-muted-foreground">Target:</span>
                  <input
                    type="number"
                    className="text-[10px] bg-transparent border-none outline-none w-16 text-muted-foreground"
                    value={widget.target ?? ''}
                    onChange={(e) =>
                      updateWidget(widget.id, {
                        target: e.target.value ? Number(e.target.value) : undefined,
                      })
                    }
                    placeholder="—"
                    aria-label="Target value"
                  />
                </div>
              )}
              {readOnly && widget.target != null && (
                <div className="text-[10px] text-muted-foreground mt-1">
                  Target: {formatValue(widget.target, widget.unit)}
                </div>
              )}

              {/* Remove */}
              {!readOnly && (
                <button
                  type="button"
                  className="text-[10px] text-muted-foreground hover:text-destructive mt-2"
                  onClick={() => removeWidget(widget.id)}
                  aria-label={`Remove ${widget.metric || 'widget'}`}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add widget */}
      {!readOnly && (
        <button
          type="button"
          className={pmBlockStyles.shared.addButton}
          onClick={addWidget}
          aria-label="Add widget"
        >
          + Add Widget
        </button>
      )}
    </div>
  );
}
