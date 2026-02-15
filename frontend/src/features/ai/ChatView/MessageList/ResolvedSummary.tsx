/**
 * ResolvedSummary - Read-only display of answered AI questions.
 *
 * Shows a collapsed chip summary that expands to reveal the full option list
 * with selection state, mirroring the interactive QuestionBlock layout.
 * Supports single-select (radio), multi-select (checkbox), and "Other" custom text.
 *
 * Design: Primary-muted background with primary border per ui-design-spec v4.0
 * Spec: specs/014-approval-input-ux/approval-input-ux-spec.md section 7.1
 */

'use client';

import { memo, useMemo } from 'react';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentQuestion } from '@/stores/ai/types/events';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Look up answer for question at index, with fallback to question-text key */
function getAnswerForQuestion(
  answers: Record<string, string>,
  question: AgentQuestion,
  index: number
): string {
  return answers[`q${index}`] ?? answers[question.question] ?? '';
}

/** Check if an option is the "Other" free-text trigger (last option with label containing "other") */
function isOtherOption(option: { label: string }, index: number, total: number): boolean {
  return index === total - 1 && /^other/i.test(option.label.trim());
}

/** Parse a comma-separated answer string into individual selected labels */
function parseSelectedLabels(answer: string): Set<string> {
  if (!answer) return new Set();
  return new Set(
    answer
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  );
}

/** Detect custom "Other" text: answer parts not matching any option label */
function extractCustomText(
  selectedLabels: Set<string>,
  options: { label: string }[]
): string | null {
  const optionLabels = new Set(options.map((o) => o.label));
  for (const label of selectedLabels) {
    if (!optionLabels.has(label)) return label;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ResolvedSummaryProps {
  resolvedAnswers: Record<string, string>;
  questions: AgentQuestion[];
  isExpanded: boolean;
  onToggle: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const ResolvedSummary = memo<ResolvedSummaryProps>(function ResolvedSummary({
  resolvedAnswers,
  questions,
  isExpanded,
  onToggle,
}) {
  // Build resolved data per question
  const resolvedQuestions = useMemo(() => {
    return questions.map((q, i) => {
      const rawAnswer = getAnswerForQuestion(resolvedAnswers, q, i);
      const selectedLabels = parseSelectedLabels(rawAnswer);
      const customText = extractCustomText(selectedLabels, q.options);

      return {
        header: q.header ?? q.question,
        question: q.question,
        answer: rawAnswer,
        options: q.options,
        isMultiSelect: q.multiSelect,
        selectedLabels,
        customText,
      };
    });
  }, [resolvedAnswers, questions]);

  // (visibleChips and overflowCount removed — now using key-value format)

  return (
    <div
      className={cn(
        'overflow-hidden transition-all duration-200',
        'rounded-[14px] border-[1.5px] border-primary/20 bg-primary-muted'
      )}
      role="region"
      aria-label="Answered question summary"
    >
      {/* Collapsed summary header */}
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        className={cn(
          'flex w-full items-start gap-2 px-3 py-2 text-left',
          'min-h-[44px] transition-colors hover:bg-primary-muted/80'
        )}
      >
        <Check className="h-3.5 w-3.5 shrink-0 text-primary mt-0.5" aria-hidden="true" />

        <div className="min-w-0 flex-1">
          {resolvedQuestions.map((rq, i) => (
            <div key={i} className="truncate text-sm">
              <span className="text-muted-foreground">{rq.header}</span>
              <span className="text-muted-foreground/50 mx-1">&rarr;</span>
              <span className="font-medium text-foreground">{rq.answer || 'Answered'}</span>
            </div>
          ))}
        </div>

        <ChevronDown
          className={cn(
            'h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200 mt-0.5',
            isExpanded && 'rotate-180'
          )}
          aria-hidden="true"
        />
      </button>

      {/* Expanded: read-only option list per question */}
      {isExpanded && (
        <div
          className={cn(
            'border-t border-primary/10 px-4 pb-3 pt-2 space-y-4',
            'motion-safe:animate-in motion-safe:fade-in motion-safe:duration-150'
          )}
        >
          {resolvedQuestions.map((rq, qIdx) => (
            <div key={qIdx} className="space-y-2">
              {/* Question text */}
              <p className="text-sm text-foreground">{rq.question}</p>

              {/* Read-only option list with selection state */}
              <div className="space-y-1.5">
                {rq.options.map((option, oIdx) => {
                  const isOther = isOtherOption(option, oIdx, rq.options.length);
                  const isSelected = isOther
                    ? rq.customText !== null || rq.selectedLabels.has(option.label)
                    : rq.selectedLabels.has(option.label);

                  return (
                    <div key={oIdx} className="flex flex-col">
                      <div
                        className={cn(
                          'flex w-full items-start gap-3 rounded-[10px] border px-3 py-2.5',
                          isSelected
                            ? 'border-ai/40 bg-ai-muted'
                            : 'border-border/50 bg-background/50 opacity-50'
                        )}
                      >
                        {/* Radio / Checkbox indicator */}
                        <div
                          aria-hidden="true"
                          className={cn(
                            'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border-2',
                            rq.isMultiSelect ? 'rounded-[3px]' : 'rounded-full',
                            isSelected ? 'border-ai bg-ai' : 'border-muted-foreground/30'
                          )}
                        >
                          {isSelected && (
                            <div
                              className={cn(
                                rq.isMultiSelect
                                  ? 'h-2.5 w-2.5 text-white'
                                  : 'h-1.5 w-1.5 rounded-full bg-white'
                              )}
                            >
                              {rq.isMultiSelect && (
                                <Check className="h-2.5 w-2.5" strokeWidth={3} />
                              )}
                            </div>
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <span className="text-sm font-medium">{option.label}</span>
                          {option.description && (
                            <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                              {option.description}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* "Other" custom text (read-only) */}
                      {isOther && isSelected && rq.customText && (
                        <div
                          className={cn(
                            'ml-7 mt-1.5 w-[calc(100%-1.75rem)] rounded-[8px] border border-border bg-muted/50',
                            'px-3 py-1.5 text-sm text-foreground'
                          )}
                        >
                          {rq.customText}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
