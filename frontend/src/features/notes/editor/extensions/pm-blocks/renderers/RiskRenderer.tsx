'use client';

/**
 * RiskRenderer — Renders Risk Register PM blocks.
 *
 * FR-032: Risk identification with probability × impact scoring
 * FR-033: Color-coded severity (green/yellow/red) + mitigation strategies
 *
 * @module pm-blocks/renderers/RiskRenderer
 */
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { pmBlockStyles } from '../pm-block-styles';
import type { PMRendererProps } from '../PMBlockNodeView';

/* ── Data types ──────────────────────────────────────────────────────── */

type MitigationStrategy = 'avoid' | 'mitigate' | 'transfer' | 'accept';

interface Risk {
  id: string;
  description: string;
  probability: number; // 1-5
  impact: number; // 1-5
  mitigation: MitigationStrategy;
  mitigationPlan?: string;
  owner?: string;
}

interface RiskData {
  title: string;
  risks: Risk[];
}

const DEFAULT_DATA: RiskData = {
  title: 'Risk Register',
  risks: [
    {
      id: 'r1',
      description: 'Example risk',
      probability: 3,
      impact: 3,
      mitigation: 'mitigate',
    },
  ],
};

/* ── Score helpers ────────────────────────────────────────────────────── */

function getScore(risk: Risk): number {
  return risk.probability * risk.impact;
}

function getScoreColor(score: number): string {
  if (score <= 6) return pmBlockStyles.risk.scoreGreen;
  if (score <= 12) return pmBlockStyles.risk.scoreYellow;
  return pmBlockStyles.risk.scoreRed;
}

const STRATEGY_LABELS: Record<MitigationStrategy, string> = {
  avoid: 'Avoid',
  mitigate: 'Mitigate',
  transfer: 'Transfer',
  accept: 'Accept',
};

/* ── Main renderer ───────────────────────────────────────────────────── */

export function RiskRenderer({ data: rawData, readOnly }: PMRendererProps) {
  const data = useMemo<RiskData>(() => {
    const merged = { ...DEFAULT_DATA, ...(rawData as Partial<RiskData>) };
    // Normalize: ensure every risk has a unique string id
    merged.risks = (merged.risks ?? []).map((r, i) => ({
      ...r,
      id: typeof r.id === 'string' && r.id ? r.id : `risk-${i}`,
    }));
    return merged;
  }, [rawData]);

  const sortedRisks = useMemo(
    () => [...data.risks].sort((a, b) => getScore(b) - getScore(a)),
    [data.risks]
  );

  return (
    <div data-testid="risk-renderer">
      <h3 className="text-base font-semibold leading-snug mb-3">{data.title}</h3>

      <div className="overflow-auto">
        <table className={pmBlockStyles.risk.table}>
          <thead>
            <tr className={pmBlockStyles.risk.headerRow}>
              <th className="p-2 text-left">Risk</th>
              <th className="p-2 text-center w-16">
                <abbr title="Probability">P</abbr>
              </th>
              <th className="p-2 text-center w-16">
                <abbr title="Impact">I</abbr>
              </th>
              <th className="p-2 text-center w-20">Score</th>
              <th className="p-2 text-left">Strategy</th>
              {!readOnly && <th className="p-2 text-left">Owner</th>}
            </tr>
          </thead>
          <tbody>
            {sortedRisks.map((risk) => {
              const score = getScore(risk);
              return (
                <tr key={risk.id}>
                  <td className="p-2 text-sm">
                    {risk.description}
                    {risk.mitigationPlan && (
                      <p className="mt-0.5 text-xs text-muted-foreground italic">
                        {risk.mitigationPlan}
                      </p>
                    )}
                  </td>
                  <td className="p-2 text-center text-sm">{risk.probability}</td>
                  <td className="p-2 text-center text-sm">{risk.impact}</td>
                  <td className={cn(pmBlockStyles.risk.scoreCell, getScoreColor(score))}>
                    {score}
                  </td>
                  <td className="p-2">
                    <span className={pmBlockStyles.risk.strategyBadge}>
                      {STRATEGY_LABELS[risk.mitigation]}
                    </span>
                  </td>
                  {!readOnly && (
                    <td className="p-2 text-xs text-muted-foreground">{risk.owner || '—'}</td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
        <span>Total: {data.risks.length} risks</span>
        <span className="text-destructive">
          High: {data.risks.filter((r) => getScore(r) > 12).length}
        </span>
        <span className="text-[#D9853F]">
          Medium: {data.risks.filter((r) => getScore(r) > 6 && getScore(r) <= 12).length}
        </span>
        <span className="text-primary">
          Low: {data.risks.filter((r) => getScore(r) <= 6).length}
        </span>
      </div>
    </div>
  );
}
