/**
 * QuestionBlock - Enhanced inline question component for QuestionRequest events.
 *
 * Rich question UI featuring:
 * - Step-by-step navigation for 3+ questions
 * - Single-select (radio) and multi-select (checkbox) modes
 * - "Other" option with inline text input (200-char limit)
 * - Collapse-to-summary after submit with expand toggle
 * - Full keyboard navigation and ARIA compliance
 *
 * Design: Warm cream background with dusty-blue AI border per ui-design-spec v4.0
 * Spec: specs/014-approval-input-ux/approval-input-ux-spec.md section 7.1
 */

'use client';

import { memo, useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { MessageSquareMore, Check, ChevronRight, ChevronLeft, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentQuestion } from '@/stores/ai/types/events';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Questions threshold for step-by-step navigation */
const STEP_THRESHOLD = 3;

/** Maximum character limit for "Other" text input */
const OTHER_TEXT_MAX_LENGTH = 200;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface QuestionBlockProps {
  /** Unique question ID (for submitting answer) */
  questionId: string;
  /** Questions to display (1-4) */
  questions: AgentQuestion[];
  /** Callback when user submits all answers */
  onSubmit: (questionId: string, answers: Record<string, string>) => void;
  /** Whether all questions have been answered */
  isResolved: boolean;
  /** Map of question text to selected answer */
  resolvedAnswers?: Record<string, string>;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Check if an option is the "Other" free-text trigger (last option with label containing "other") */
function isOtherOption(option: { label: string }, index: number, total: number): boolean {
  return index === total - 1 && /^other/i.test(option.label.trim());
}

/** Build a display string from selected option labels */
function buildAnswerString(
  question: AgentQuestion,
  selected: Set<number>,
  otherText: string
): string {
  const labels: string[] = [];
  for (const idx of selected) {
    const opt = question.options[idx];
    if (opt) {
      if (isOtherOption(opt, idx, question.options.length) && otherText.trim()) {
        labels.push(otherText.trim());
      } else {
        labels.push(opt.label);
      }
    }
  }
  return labels.join(', ') || '';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface OptionButtonProps {
  option: { label: string; description?: string };
  isSelected: boolean;
  isMultiSelect: boolean;
  isDisabled: boolean;
  isOther: boolean;
  otherText: string;
  onSelect: () => void;
  onOtherTextChange: (value: string) => void;
}

/** Single option row with radio/checkbox indicator */
const OptionButton = memo<OptionButtonProps>(function OptionButton({
  option,
  isSelected,
  isMultiSelect,
  isDisabled,
  isOther,
  otherText,
  onSelect,
  onOtherTextChange,
}) {
  const otherInputRef = useRef<HTMLInputElement>(null);

  // Auto-focus the "Other" text input when selected
  useEffect(() => {
    if (isOther && isSelected && otherInputRef.current) {
      otherInputRef.current.focus();
    }
  }, [isOther, isSelected]);

  return (
    <div className="flex flex-col">
      <button
        type="button"
        role={isMultiSelect ? 'checkbox' : 'radio'}
        aria-checked={isSelected}
        aria-label={option.description ? `${option.label}: ${option.description}` : option.label}
        disabled={isDisabled}
        onClick={onSelect}
        onKeyDown={(e) => {
          if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault();
            onSelect();
          }
        }}
        className={cn(
          'flex w-full items-start gap-3 rounded-[10px] border px-3 py-2.5 text-left',
          'transition-all duration-150 min-h-[44px]',
          isSelected
            ? 'border-ai/40 bg-ai-muted'
            : 'border-border bg-background hover:border-ai/30 hover:bg-ai-muted/50',
          isDisabled && 'pointer-events-none opacity-50'
        )}
      >
        {/* Radio / Checkbox indicator */}
        <div
          aria-hidden="true"
          className={cn(
            'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center border-2 transition-colors',
            isMultiSelect ? 'rounded-[3px]' : 'rounded-full',
            isSelected ? 'border-ai bg-ai' : 'border-muted-foreground/30'
          )}
        >
          {isSelected && (
            <div
              className={cn(
                isMultiSelect ? 'h-2.5 w-2.5 text-white' : 'h-1.5 w-1.5 rounded-full bg-white'
              )}
            >
              {isMultiSelect && <Check className="h-2.5 w-2.5" strokeWidth={3} />}
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
      </button>

      {/* Inline "Other" text input */}
      {isOther && isSelected && (
        <input
          ref={otherInputRef}
          type="text"
          value={otherText}
          maxLength={OTHER_TEXT_MAX_LENGTH}
          onChange={(e) => onOtherTextChange(e.target.value)}
          placeholder="Type your answer..."
          disabled={isDisabled}
          aria-label="Custom answer text"
          className={cn(
            'ml-7 mt-1.5 w-[calc(100%-1.75rem)] rounded-[8px] border border-border bg-background',
            'px-3 py-1.5 text-sm placeholder:text-muted-foreground',
            'focus:border-ai focus:outline-none focus:ring-2 focus:ring-ai/20',
            'transition-all duration-150',
            isDisabled && 'pointer-events-none opacity-50'
          )}
        />
      )}
    </div>
  );
});

// Extracted to own file for 700-line limit; re-exported for backward compatibility
import { ResolvedSummary } from './ResolvedSummary';
export { ResolvedSummary } from './ResolvedSummary';
export type { ResolvedSummaryProps } from './ResolvedSummary';

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const QuestionBlock = memo<QuestionBlockProps>(function QuestionBlock({
  questionId,
  questions,
  onSubmit,
  isResolved,
  resolvedAnswers,
  className,
}) {
  // ---- State ----
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedOptions, setSelectedOptions] = useState<Map<number, Set<number>>>(new Map());
  const [otherTexts, setOtherTexts] = useState<Map<number, string>>(new Map());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExpandedAfterResolve, setIsExpandedAfterResolve] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const liveRegionRef = useRef<HTMLDivElement>(null);

  const useStepping = questions.length >= STEP_THRESHOLD;
  const totalSteps = questions.length;

  /** Check if a question should be skipped based on skipWhen conditions and current answers. */
  const shouldSkipQuestion = useCallback(
    (qIdx: number): boolean => {
      const q = questions[qIdx];
      if (!q?.skipWhen?.length) return false;
      return q.skipWhen.some((cond) => {
        const selected = selectedOptions.get(cond.questionIndex);
        if (!selected) return false;
        const refQ = questions[cond.questionIndex];
        if (!refQ) return false;
        return [...selected].some((idx) => refQ.options[idx]?.label === cond.selectedLabel);
      });
    },
    [questions, selectedOptions]
  );

  /** Find the next visible (non-skipped) step in the given direction. */
  const getNextVisibleStep = useCallback(
    (fromStep: number, direction: 1 | -1): number => {
      let step = fromStep + direction;
      while (step >= 0 && step < totalSteps) {
        if (!shouldSkipQuestion(step)) return step;
        step += direction;
      }
      return fromStep; // No valid step found — stay put
    },
    [totalSteps, shouldSkipQuestion]
  );

  /** Find the last visible step (for isLastStep check). */
  const lastVisibleStep = useMemo(() => {
    for (let i = totalSteps - 1; i >= 0; i--) {
      if (!shouldSkipQuestion(i)) return i;
    }
    return totalSteps - 1;
  }, [totalSteps, shouldSkipQuestion]);

  const isLastStep = currentStep >= lastVisibleStep;

  // ---- Derived ----

  /** Whether the current step has a valid selection */
  const currentStepHasSelection = useMemo(() => {
    const selected = selectedOptions.get(currentStep);
    if (!selected || selected.size === 0) return false;

    // If "Other" is selected, require non-empty text
    const q = questions[currentStep];
    if (q) {
      for (const idx of selected) {
        const opt = q.options[idx];
        if (opt && isOtherOption(opt, idx, q.options.length)) {
          const text = otherTexts.get(currentStep) ?? '';
          if (!text.trim()) return false;
        }
      }
    }
    return true;
  }, [selectedOptions, otherTexts, currentStep, questions]);

  /** Whether all visible (non-skipped) questions have valid selections. */
  const allQuestionsAnswered = useMemo(() => {
    for (let i = 0; i < questions.length; i++) {
      // Skip questions whose skipWhen conditions are met
      if (shouldSkipQuestion(i)) continue;

      const selected = selectedOptions.get(i);
      if (!selected || selected.size === 0) return false;

      const q = questions[i];
      if (!q) return false;
      for (const idx of selected) {
        const opt = q.options[idx];
        if (opt && isOtherOption(opt, idx, q.options.length)) {
          const text = otherTexts.get(i) ?? '';
          if (!text.trim()) return false;
        }
      }
    }
    return true;
  }, [selectedOptions, otherTexts, questions, shouldSkipQuestion]);

  /** Can submit: in stepping mode, must be on last step with all answered; otherwise all answered */
  const canSubmit = useStepping ? isLastStep && allQuestionsAnswered : allQuestionsAnswered;

  // ---- Callbacks ----

  const toggleOption = useCallback(
    (questionIdx: number, optionIdx: number, multiSelect: boolean) => {
      if (isSubmitting) return;

      setSelectedOptions((prev) => {
        const next = new Map(prev);
        const current = next.get(questionIdx) ?? new Set<number>();

        if (multiSelect) {
          const updated = new Set(current);
          if (updated.has(optionIdx)) {
            updated.delete(optionIdx);
          } else {
            updated.add(optionIdx);
          }
          next.set(questionIdx, updated);
        } else {
          next.set(questionIdx, new Set([optionIdx]));
        }

        return next;
      });
    },
    [isSubmitting]
  );

  const updateOtherText = useCallback(
    (questionIdx: number, value: string) => {
      if (isSubmitting) return;
      setOtherTexts((prev) => {
        const next = new Map(prev);
        next.set(questionIdx, value);
        return next;
      });
    },
    [isSubmitting]
  );

  const handleNext = useCallback(() => {
    if (currentStep < totalSteps - 1 && currentStepHasSelection) {
      const next = getNextVisibleStep(currentStep, 1);
      if (next !== currentStep) setCurrentStep(next);
    }
  }, [currentStep, totalSteps, currentStepHasSelection, getNextVisibleStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      const prev = getNextVisibleStep(currentStep, -1);
      if (prev !== currentStep) setCurrentStep(prev);
    }
  }, [currentStep, getNextVisibleStep]);

  const handleSubmit = useCallback(() => {
    if (!canSubmit || isSubmitting) return;

    setIsSubmitting(true);

    // Build answers record keyed by index (q0, q1, ...) matching backend format
    // Skipped questions get empty string value
    const answers: Record<string, string> = {};
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      if (!q) continue;
      if (shouldSkipQuestion(i)) {
        answers[`q${i}`] = '';
        continue;
      }
      const selected = selectedOptions.get(i) ?? new Set<number>();
      const otherText = otherTexts.get(i) ?? '';
      answers[`q${i}`] = buildAnswerString(q, selected, otherText);
    }

    onSubmit(questionId, answers);
  }, [
    canSubmit,
    isSubmitting,
    questionId,
    questions,
    selectedOptions,
    otherTexts,
    onSubmit,
    shouldSkipQuestion,
  ]);

  // Keyboard shortcuts at container level
  const handleContainerKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!useStepping) return;

      if (e.key === 'Enter' && !e.shiftKey && currentStepHasSelection && !isLastStep) {
        e.preventDefault();
        handleNext();
      } else if (e.key === 'Enter' && e.shiftKey && currentStep > 0) {
        e.preventDefault();
        handleBack();
      }
    },
    [useStepping, currentStepHasSelection, isLastStep, currentStep, handleNext, handleBack]
  );

  // Announce step changes to screen readers
  useEffect(() => {
    if (useStepping && liveRegionRef.current) {
      const q = questions[currentStep];
      liveRegionRef.current.textContent = `Question ${currentStep + 1} of ${totalSteps}: ${q?.question ?? ''}`;
    }
  }, [currentStep, useStepping, totalSteps, questions]);

  // ---- Header label (must be before early return to satisfy hooks rules) ----
  const headerLabel = useMemo(() => {
    const firstQuestion = questions[0];
    if (questions.length === 1 && firstQuestion?.header) {
      return firstQuestion.header;
    }
    return 'Agent needs your input';
  }, [questions]);

  // ---- Resolved state ----

  if (isResolved && resolvedAnswers) {
    return (
      <div
        className={cn(
          'motion-safe:animate-in motion-safe:fade-in motion-safe:duration-250',
          className
        )}
      >
        <ResolvedSummary
          resolvedAnswers={resolvedAnswers}
          questions={questions}
          isExpanded={isExpandedAfterResolve}
          onToggle={() => setIsExpandedAfterResolve((v) => !v)}
        />
      </div>
    );
  }

  // ---- Determine which questions to render ----
  const visibleQuestions = useStepping ? [questions[currentStep]] : questions;
  const visibleStartIndex = useStepping ? currentStep : 0;

  return (
    <div
      ref={containerRef}
      className={cn(
        'rounded-[12px] border border-border/60 border-l-[3px] border-l-ai',
        'bg-[var(--color-question-bg)] dark:bg-[var(--color-question-bg-dark)]',
        'shadow-[0_1px_4px_rgba(0,0,0,0.04)]',
        'motion-safe:animate-in motion-safe:slide-in-from-bottom-3 motion-safe:duration-200',
        className
      )}
      role="region"
      aria-label={`Agent question: ${headerLabel}`}
      onKeyDown={handleContainerKeyDown}
    >
      {/* Screen reader live region for step announcements */}
      <div ref={liveRegionRef} className="sr-only" aria-live="polite" aria-atomic="true" />

      {/* Header */}
      <div className="flex items-center gap-2 px-4 pb-2 pt-3">
        <MessageSquareMore className="h-4 w-4 text-ai" aria-hidden="true" />
        <span className="text-sm font-medium">{headerLabel}</span>

        {/* Step indicator */}
        {useStepping && (
          <span className="ml-auto text-xs tabular-nums text-muted-foreground">
            {currentStep + 1}/{totalSteps}
          </span>
        )}
      </div>

      {/* Questions */}
      <div className="space-y-4 px-4 pb-3">
        {visibleQuestions.map((q, relIdx) => {
          if (!q) return null;
          const qIdx = visibleStartIndex + relIdx;

          return (
            <div key={qIdx} className="space-y-2">
              <p className="text-sm text-foreground">{q.question}</p>

              {/* Options */}
              <div
                role={q.multiSelect ? 'group' : 'radiogroup'}
                aria-label={q.question}
                className="space-y-1.5"
              >
                {q.options.map((option, oIdx) => {
                  const isSelected = selectedOptions.get(qIdx)?.has(oIdx) ?? false;
                  const isOther = isOtherOption(option, oIdx, q.options.length);

                  return (
                    <OptionButton
                      key={oIdx}
                      option={option}
                      isSelected={isSelected}
                      isMultiSelect={q.multiSelect}
                      isDisabled={isSubmitting}
                      isOther={isOther}
                      otherText={otherTexts.get(qIdx) ?? ''}
                      onSelect={() => toggleOption(qIdx, oIdx, q.multiSelect)}
                      onOtherTextChange={(v) => updateOtherText(qIdx, v)}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* Navigation + Submit footer */}
        <div className="flex items-center gap-2">
          {/* Back button (stepping mode only) */}
          {useStepping && currentStep > 0 && (
            <button
              type="button"
              onClick={handleBack}
              disabled={isSubmitting}
              className={cn(
                'flex items-center gap-1 rounded-[10px] border border-border px-3 py-2',
                'text-sm text-muted-foreground transition-colors',
                'hover:bg-muted min-h-[44px]',
                'disabled:pointer-events-none disabled:opacity-50'
              )}
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
              Back
            </button>
          )}

          <div className="flex-1" />

          {/* Next button (stepping mode, not last step) */}
          {useStepping && !isLastStep && (
            <button
              type="button"
              onClick={handleNext}
              disabled={!currentStepHasSelection || isSubmitting}
              className={cn(
                'flex items-center gap-1 rounded-[10px] px-4 py-2 text-sm font-medium transition-colors',
                'min-h-[44px]',
                currentStepHasSelection && !isSubmitting
                  ? 'bg-ai text-white hover:bg-ai-hover'
                  : 'cursor-not-allowed bg-muted text-muted-foreground'
              )}
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          )}

          {/* Submit button (last step in stepping mode, or always in non-stepping) */}
          {(!useStepping || isLastStep) && (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit || isSubmitting}
              aria-busy={isSubmitting}
              className={cn(
                'flex items-center gap-2 rounded-[10px] px-4 py-2 text-sm font-medium transition-colors',
                'min-h-[44px]',
                canSubmit && !isSubmitting
                  ? 'bg-primary text-white hover:bg-primary-hover'
                  : 'cursor-not-allowed bg-muted text-muted-foreground'
              )}
            >
              {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

QuestionBlock.displayName = 'QuestionBlock';
