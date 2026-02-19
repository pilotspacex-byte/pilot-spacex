'use client';

/**
 * DecisionRenderer — Renders Decision Record PM blocks.
 *
 * FR-020: State machine (Open → Decided → Superseded)
 * FR-021: Binary (Yes/No) or multi-option (max 6)
 * FR-022: Pros/cons/effort/risk per option
 * FR-023: Decision recording with rationale + date
 * FR-024: Create Issue from decision
 *
 * @module pm-blocks/renderers/DecisionRenderer
 */
import { useCallback, useMemo } from 'react';
import { Check, Circle, AlertTriangle, Plus, ArrowRight, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlockStyles } from '../pm-block-styles';
import type { PMRendererProps } from '../PMBlockNodeView';

/* ── Data types ──────────────────────────────────────────────────────── */

type DecisionStatus = 'open' | 'decided' | 'superseded';

interface DecisionOption {
  id: string;
  label: string;
  description?: string;
  pros: string[];
  cons: string[];
  effort?: string;
  risk?: string;
}

interface DecisionData {
  title: string;
  description?: string;
  type: 'binary' | 'multi-option';
  status: DecisionStatus;
  options: DecisionOption[];
  selectedOptionId?: string;
  rationale?: string;
  decisionDate?: string;
  linkedIssueIds: string[];
  supersededBy?: string;
}

const DEFAULT_DATA: DecisionData = {
  title: 'Untitled Decision',
  type: 'binary',
  status: 'open',
  options: [
    { id: 'opt-1', label: 'Option A', pros: [], cons: [] },
    { id: 'opt-2', label: 'Option B', pros: [], cons: [] },
  ],
  linkedIssueIds: [],
};

/* ── Status helpers ──────────────────────────────────────────────────── */

const STATUS_CONFIG: Record<
  DecisionStatus,
  { label: string; icon: typeof Check; className: string }
> = {
  open: {
    label: 'Open',
    icon: Circle,
    className: pmBlockStyles.decision.statusOpen,
  },
  decided: {
    label: 'Decided',
    icon: Check,
    className: pmBlockStyles.decision.statusDecided,
  },
  superseded: {
    label: 'Superseded',
    icon: AlertTriangle,
    className: pmBlockStyles.decision.statusSuperseded,
  },
};

/* ── Sub-components ──────────────────────────────────────────────────── */

function StatusBanner({
  status,
  onStatusChange,
  readOnly,
}: {
  status: DecisionStatus;
  onStatusChange: (s: DecisionStatus) => void;
  readOnly: boolean;
}) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <div
      className={cn(pmBlockStyles.decision.statusBanner, config.className)}
      role="status"
      aria-label={`Decision status: ${config.label}`}
    >
      <Icon className="size-3.5" />
      <span>{config.label}</span>

      {!readOnly && status === 'open' && (
        <button
          type="button"
          className="ml-auto text-[10px] opacity-70 hover:opacity-100 transition-opacity inline-flex items-center gap-0.5 px-2 py-1"
          onClick={() => onStatusChange('decided')}
          aria-label="Mark as decided"
        >
          Decide <ArrowRight className="size-3" aria-hidden="true" />
        </button>
      )}
      {!readOnly && status === 'decided' && (
        <button
          type="button"
          className="ml-auto text-[10px] opacity-70 hover:opacity-100 transition-opacity inline-flex items-center gap-0.5 px-2 py-1"
          onClick={() => onStatusChange('superseded')}
          aria-label="Mark as superseded"
        >
          Supersede <ArrowRight className="size-3" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

function OptionCard({
  option,
  isSelected,
  onSelect,
  readOnly,
}: {
  option: DecisionOption;
  isSelected: boolean;
  onSelect: () => void;
  readOnly: boolean;
}) {
  return (
    <div
      className={cn(
        pmBlockStyles.decision.optionCard,
        isSelected && pmBlockStyles.decision.optionCardSelected
      )}
      role="radio"
      aria-checked={isSelected}
      tabIndex={readOnly ? -1 : 0}
      data-testid={`option-card-${option.id}`}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !readOnly) {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className={pmBlockStyles.decision.optionTitle}>
          {isSelected && <Check className="inline size-3.5 mr-1 text-primary" />}
          {option.label}
        </h4>
        {!readOnly && !isSelected && (
          <button
            type="button"
            tabIndex={-1}
            className="shrink-0 text-xs text-muted-foreground hover:text-foreground"
            onClick={onSelect}
            aria-label={`Select ${option.label}`}
          >
            Select
          </button>
        )}
      </div>

      {option.description && (
        <p className={pmBlockStyles.decision.optionDescription}>{option.description}</p>
      )}

      {/* Pros */}
      {option.pros.length > 0 && (
        <ul className="mt-2 space-y-0.5" aria-label="Pros">
          {option.pros.map((pro, i) => (
            <li key={i} className={pmBlockStyles.decision.prosItem}>
              <span className="shrink-0">+</span>
              <span>{pro}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Cons */}
      {option.cons.length > 0 && (
        <ul className="mt-1 space-y-0.5" aria-label="Cons">
          {option.cons.map((con, i) => (
            <li key={i} className={pmBlockStyles.decision.consItem}>
              <span className="shrink-0">−</span>
              <span>{con}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Effort / Risk badges */}
      {(option.effort || option.risk) && (
        <div className="mt-2 flex gap-1.5">
          {option.effort && (
            <span className={pmBlockStyles.decision.optionBadge}>Effort: {option.effort}</span>
          )}
          {option.risk && (
            <span className={pmBlockStyles.decision.optionBadge}>Risk: {option.risk}</span>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main renderer ───────────────────────────────────────────────────── */

export function DecisionRenderer({
  data: rawData,
  readOnly,
  onDataChange,
  onCreateIssue,
}: PMRendererProps) {
  const data = useMemo<DecisionData>(() => {
    return { ...DEFAULT_DATA, ...(rawData as Partial<DecisionData>) };
  }, [rawData]);

  const updateData = useCallback(
    (partial: Partial<DecisionData>) => {
      onDataChange({ ...data, ...partial });
    },
    [data, onDataChange]
  );

  const handleStatusChange = useCallback(
    (status: DecisionStatus) => {
      const updates: Partial<DecisionData> = { status };
      if (status === 'decided') {
        updates.decisionDate = new Date().toISOString().split('T')[0];
      }
      updateData(updates);
    },
    [updateData]
  );

  const handleSelectOption = useCallback(
    (optionId: string) => {
      updateData({ selectedOptionId: optionId });
    },
    [updateData]
  );

  return (
    <div data-testid="decision-renderer" className={pmBlockStyles.shared.container}>
      {/* Status banner */}
      <StatusBanner status={data.status} onStatusChange={handleStatusChange} readOnly={readOnly} />

      {/* Header */}
      <div className={cn('px-4 pt-3', pmBlockStyles.shared.header)}>
        <h3 className="text-base font-semibold leading-snug">{data.title}</h3>
        {data.description && (
          <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{data.description}</p>
        )}
      </div>

      {/* Options grid — radiogroup semantics */}
      <div
        className={cn('px-4 pt-3', pmBlockStyles.decision.optionGrid)}
        role="radiogroup"
        aria-label="Decision options"
        onKeyDown={(e) => {
          if (readOnly) return;
          const currentIdx = data.options.findIndex((o) => o.id === data.selectedOptionId);
          let nextIdx: number | null = null;
          if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
            e.preventDefault();
            nextIdx = (currentIdx + 1) % data.options.length;
          } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
            e.preventDefault();
            nextIdx = currentIdx <= 0 ? data.options.length - 1 : currentIdx - 1;
          }
          if (nextIdx !== null) {
            const nextOption = data.options[nextIdx];
            if (nextOption) handleSelectOption(nextOption.id);
          }
        }}
      >
        {data.options.map((option, idx) => (
          <OptionCard
            key={option.id || `opt-${idx}`}
            option={option}
            isSelected={option.id === data.selectedOptionId}
            onSelect={() => handleSelectOption(option.id)}
            readOnly={readOnly || data.status !== 'open'}
          />
        ))}
      </div>

      {/* Rationale */}
      {data.rationale && (
        <div className={cn('mx-4', pmBlockStyles.decision.rationale)}>{data.rationale}</div>
      )}

      {/* Decision metadata */}
      {data.decisionDate && (
        <div className={cn('px-4', pmBlockStyles.decision.decisionMeta)}>
          <Calendar className="size-3" />
          <span>Decided on {data.decisionDate}</span>
        </div>
      )}

      {/* Create Issue button */}
      {data.status === 'decided' && !readOnly && (
        <div className={cn('px-4', pmBlockStyles.decision.createIssueButton)}>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-accent transition-colors"
            aria-label="Create issue from decision"
            onClick={() =>
              onCreateIssue?.({
                blockType: 'decision',
                data: data as unknown as Record<string, unknown>,
              })
            }
          >
            <Plus className="size-3" />
            Create Issue
          </button>
        </div>
      )}

      {/* Superseded indicator */}
      {data.status === 'superseded' && data.supersededBy && (
        <div className="px-4 pb-2 flex items-center gap-1 text-xs text-muted-foreground">
          <ArrowRight className="size-3" />
          <span>Superseded by: {data.supersededBy}</span>
        </div>
      )}
    </div>
  );
}
