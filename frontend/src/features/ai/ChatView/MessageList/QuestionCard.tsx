/**
 * QuestionCard - Inline question card for AskUserQuestion events.
 *
 * Renders when the AI agent needs clarification during execution.
 * Shows question, options, and optional free-text input.
 * After answering, collapses to a single-line summary.
 *
 * Design: Warm cream background with teal-green border per ui-design-spec.md v4.0
 */

'use client';

import { memo, useState, useCallback } from 'react';
import { HelpCircle, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentQuestion } from '@/stores/ai/types/events';

interface QuestionCardProps {
  /** Unique question ID (for submitting answer) */
  questionId: string;
  /** Questions to display */
  questions: AgentQuestion[];
  /** Callback when user submits answer */
  onSubmit: (questionId: string, answer: string) => void;
  /** Whether this question has been answered */
  isResolved: boolean;
  /** The answer that was submitted */
  resolvedAnswer?: string;
  /** Additional CSS classes */
  className?: string;
}

export const QuestionCard = memo<QuestionCardProps>(
  ({ questionId, questions, onSubmit, isResolved, resolvedAnswer, className }) => {
    const [selectedOptions, setSelectedOptions] = useState<Map<number, Set<number>>>(new Map());
    const [freeText, setFreeText] = useState('');

    const toggleOption = useCallback(
      (questionIdx: number, optionIdx: number, multiSelect: boolean) => {
        setSelectedOptions((prev) => {
          const next = new Map(prev);
          const current = next.get(questionIdx) ?? new Set<number>();

          if (multiSelect) {
            const updated = new Set(current);
            if (updated.has(optionIdx)) updated.delete(optionIdx);
            else updated.add(optionIdx);
            next.set(questionIdx, updated);
          } else {
            next.set(questionIdx, new Set([optionIdx]));
          }

          return next;
        });
      },
      []
    );

    const handleSubmit = useCallback(() => {
      // Build answer from selected options + free text
      const parts: string[] = [];
      questions.forEach((q, qIdx) => {
        const selected = selectedOptions.get(qIdx);
        if (selected && selected.size > 0) {
          const labels = Array.from(selected).map((i) => q.options[i]?.label ?? '');
          parts.push(labels.join(', '));
        }
      });

      if (freeText.trim()) {
        parts.push(freeText.trim());
      }

      const answer = parts.join(' | ') || 'No selection';
      onSubmit(questionId, answer);
    }, [questionId, questions, selectedOptions, freeText, onSubmit]);

    const hasSelection =
      Array.from(selectedOptions.values()).some((s) => s.size > 0) || freeText.trim();

    // Collapsed state after answering
    if (isResolved) {
      return (
        <div
          className={cn(
            'flex items-center gap-2 rounded-[10px] border border-primary/20 bg-primary-muted px-3 py-2',
            className
          )}
        >
          <Check className="h-3.5 w-3.5 text-primary" />
          <span className="text-sm text-muted-foreground">
            Answered: <span className="font-medium text-foreground">{resolvedAnswer}</span>
          </span>
        </div>
      );
    }

    return (
      <div
        className={cn(
          'rounded-[12px] border-[1.5px] border-primary/30 bg-[#F5F0EB] dark:bg-[#252220]',
          'shadow-[0_2px_8px_rgba(0,0,0,0.06)]',
          'animate-in slide-in-from-bottom-2 duration-200',
          className
        )}
        role="region"
        aria-label="Agent question"
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 pt-3 pb-2">
          <HelpCircle className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Agent needs your input</span>
        </div>

        {/* Questions */}
        <div className="space-y-4 px-4 pb-3">
          {questions.map((q, qIdx) => (
            <div key={qIdx} className="space-y-2">
              <p className="text-sm text-foreground">{q.question}</p>

              {/* Options */}
              <div className="space-y-1">
                {q.options.map((option, oIdx) => {
                  const isSelected = selectedOptions.get(qIdx)?.has(oIdx) ?? false;

                  return (
                    <button
                      key={oIdx}
                      type="button"
                      onClick={() => toggleOption(qIdx, oIdx, q.multiSelect)}
                      className={cn(
                        'flex w-full items-start gap-3 rounded-[10px] border px-3 py-2.5 text-left transition-all duration-150',
                        isSelected
                          ? 'border-primary/40 bg-primary-muted'
                          : 'border-border bg-background hover:bg-primary-muted/50'
                      )}
                    >
                      {/* Radio / Checkbox indicator */}
                      <div
                        className={cn(
                          'mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 transition-colors',
                          q.multiSelect && 'rounded',
                          isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/30'
                        )}
                      >
                        {isSelected && (
                          <div className="flex h-full items-center justify-center">
                            <div className="h-1.5 w-1.5 rounded-full bg-white" />
                          </div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium">{option.label}</span>
                        {option.description && (
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {option.description}
                          </p>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Free text input */}
          <input
            type="text"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && hasSelection) handleSubmit();
            }}
            placeholder="Or type a custom answer..."
            className={cn(
              'w-full rounded-[10px] border border-border bg-background px-3 py-2',
              'text-sm placeholder:text-muted-foreground',
              'focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20'
            )}
            aria-label="Custom answer"
          />

          {/* Submit */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!hasSelection}
            className={cn(
              'rounded-[10px] px-4 py-2 text-sm font-medium transition-colors',
              hasSelection
                ? 'bg-primary text-white hover:bg-primary-hover'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            )}
          >
            Submit
          </button>
        </div>
      </div>
    );
  }
);

QuestionCard.displayName = 'QuestionCard';
