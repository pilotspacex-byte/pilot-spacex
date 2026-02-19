'use client';

/**
 * RACIRenderer — Renders RACI Matrix PM blocks.
 *
 * FR-030: RACI assignment matrix (R=Responsible, A=Accountable, C=Consulted, I=Informed)
 * FR-031: Constraint validation (exactly one A per deliverable)
 *
 * @module pm-blocks/renderers/RACIRenderer
 */
import { useCallback, useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlockStyles } from '../pm-block-styles';
import type { PMRendererProps } from '../PMBlockNodeView';

/* ── Data types ──────────────────────────────────────────────────────── */

type RACIRole = 'R' | 'A' | 'C' | 'I' | '';

interface RACIData {
  title: string;
  deliverables: string[];
  stakeholders: string[];
  assignments: Record<string, Record<string, RACIRole>>;
}

/** AI may produce deliverables as objects with inline role assignments */
interface RACIDeliverableObject {
  name: string;
  roleAssignments: Record<string, RACIRole>;
}

const DEFAULT_DATA: RACIData = {
  title: 'RACI Matrix',
  deliverables: ['Deliverable 1', 'Deliverable 2'],
  stakeholders: ['Person A', 'Person B', 'Person C'],
  assignments: {},
};

/** Normalize AI-generated format (object deliverables) into flat RACIData */
function normalizeRaciData(raw: Record<string, unknown>): RACIData {
  const base = { ...DEFAULT_DATA, ...raw };
  const rawDeliverables = (raw.deliverables ?? base.deliverables) as
    | string[]
    | RACIDeliverableObject[];

  if (
    !Array.isArray(rawDeliverables) ||
    rawDeliverables.length === 0 ||
    rawDeliverables.every((d) => typeof d === 'string')
  ) {
    return base as RACIData;
  }

  // Object format: extract names, merge assignments, derive stakeholders
  const objectDeliverables = rawDeliverables as RACIDeliverableObject[];
  const deliverables: string[] = [];
  const assignments: Record<string, Record<string, RACIRole>> = {
    ...(base.assignments as Record<string, Record<string, RACIRole>>),
  };
  const stakeholderSet = new Set<string>(
    Array.isArray(base.stakeholders) ? (base.stakeholders as string[]) : []
  );

  for (const d of objectDeliverables) {
    const name = typeof d === 'object' && d.name ? String(d.name) : String(d);
    deliverables.push(name);
    if (typeof d === 'object' && d.roleAssignments) {
      assignments[name] = d.roleAssignments;
      for (const s of Object.keys(d.roleAssignments)) stakeholderSet.add(s);
    }
  }

  return {
    title: (base.title as string) ?? DEFAULT_DATA.title,
    deliverables,
    stakeholders: stakeholderSet.size > 0 ? Array.from(stakeholderSet) : DEFAULT_DATA.stakeholders,
    assignments,
  };
}

const ROLE_CYCLE: RACIRole[] = ['', 'R', 'A', 'C', 'I'];

const ROLE_STYLES: Record<string, string> = {
  R: pmBlockStyles.raci.cellR,
  A: pmBlockStyles.raci.cellA,
  C: pmBlockStyles.raci.cellC,
  I: pmBlockStyles.raci.cellI,
};

/* ── Validation ──────────────────────────────────────────────────────── */

function validateRaci(data: RACIData): Map<string, string> {
  const warnings = new Map<string, string>();

  for (const deliverable of data.deliverables) {
    const assignments = data.assignments[deliverable] ?? {};
    const accountableCount = Object.values(assignments).filter((r) => r === 'A').length;

    if (accountableCount === 0) {
      warnings.set(deliverable, 'Missing Accountable (A) — exactly one required');
    } else if (accountableCount > 1) {
      warnings.set(
        deliverable,
        `${accountableCount} Accountable (A) assigned — exactly one required`
      );
    }
  }

  return warnings;
}

/* ── Main renderer ───────────────────────────────────────────────────── */

export function RACIRenderer({ data: rawData, readOnly, onDataChange }: PMRendererProps) {
  const data = useMemo<RACIData>(() => {
    return normalizeRaciData((rawData ?? {}) as Record<string, unknown>);
  }, [rawData]);

  const warnings = useMemo(() => validateRaci(data), [data]);

  const handleCellClick = useCallback(
    (deliverable: string, stakeholder: string) => {
      if (readOnly) return;

      const current = data.assignments[deliverable]?.[stakeholder] ?? '';
      const currentIdx = ROLE_CYCLE.indexOf(current);
      const nextRole = ROLE_CYCLE[(currentIdx + 1) % ROLE_CYCLE.length];

      const newAssignments = {
        ...data.assignments,
        [deliverable]: {
          ...(data.assignments[deliverable] ?? {}),
          [stakeholder]: nextRole,
        },
      };

      onDataChange({ ...data, assignments: newAssignments });
    },
    [data, readOnly, onDataChange]
  );

  return (
    <div data-testid="raci-renderer">
      <h3 className="text-base font-semibold leading-snug mb-3">{data.title}</h3>

      <div className={pmBlockStyles.raci.grid}>
        <table className="w-full border-collapse text-sm" role="grid">
          <thead>
            <tr>
              <th className={cn(pmBlockStyles.raci.headerCell, 'text-left')}>Deliverable</th>
              {data.stakeholders.map((s) => (
                <th key={s} className={pmBlockStyles.raci.headerCell}>
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.deliverables.map((d) => {
              const hasWarning = warnings.has(d);
              return (
                <tr key={d} className={hasWarning ? pmBlockStyles.raci.validationError : ''}>
                  <td className={pmBlockStyles.raci.deliverableCell}>{d}</td>
                  {data.stakeholders.map((s) => {
                    const role = data.assignments[d]?.[s] ?? '';
                    return (
                      <td
                        key={s}
                        className={cn(pmBlockStyles.raci.cell, role && ROLE_STYLES[role])}
                        onClick={() => handleCellClick(d, s)}
                        role="gridcell"
                        tabIndex={readOnly ? -1 : 0}
                        aria-label={`${d} - ${s}: ${role || 'unassigned'}`}
                        title="Click to cycle: R (Responsible) → A (Accountable) → C (Consulted) → I (Informed) → empty"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleCellClick(d, s);
                          }
                        }}
                      >
                        {role}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Validation warnings */}
      {warnings.size > 0 && (
        <div className="mt-2 space-y-1">
          {Array.from(warnings.entries()).map(([deliverable, warning]) => (
            <div key={deliverable} className={pmBlockStyles.raci.validationWarning}>
              <AlertTriangle className="inline size-3 mr-1" />
              <span>
                {deliverable}: {warning}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
