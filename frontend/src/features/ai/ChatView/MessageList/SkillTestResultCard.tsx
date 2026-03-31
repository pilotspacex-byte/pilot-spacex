/**
 * SkillTestResultCard — inline test result display in ChatView.
 *
 * Shows score bar (0-10), pass/fail checklist, collapsible suggestions,
 * and a Refine action button.
 *
 * NOT observer() — use React.memo with local useState.
 * Phase 64-03
 */
'use client';

import { memo, useState } from 'react';
import { ClipboardCheck, CheckCircle, XCircle, ChevronRight, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface SkillTestResultCardProps {
  skillName: string;
  /** Aggregate score 0–10 */
  score: number;
  /** Descriptions of passing test cases */
  passed: string[];
  /** Descriptions of failing test cases */
  failed: string[];
  /** Suggested improvements */
  suggestions: string[];
  /** Representative sample output */
  sampleOutput: string;
  onRefine?: () => void;
}

/**
 * Determine badge variant based on score.
 * >= 8 → default (green-ish), >= 5 → secondary (yellow-ish), < 5 → destructive (red)
 */
function scoreBadgeVariant(score: number): 'default' | 'secondary' | 'destructive' {
  if (score >= 8) return 'default';
  if (score >= 5) return 'secondary';
  return 'destructive';
}

/**
 * Score bar color class based on score.
 */
function scoreBarClass(score: number): string {
  if (score >= 8) return 'bg-green-500';
  if (score >= 5) return 'bg-yellow-500';
  return 'bg-red-500';
}

export const SkillTestResultCard = memo<SkillTestResultCardProps>(function SkillTestResultCard({
  skillName,
  score,
  passed,
  failed,
  suggestions,
  sampleOutput: _sampleOutput,
  onRefine,
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div
      className="mx-4 my-3 rounded-[14px] border bg-background p-4 animate-fade-up"
      role="region"
      aria-label={`Test results for ${skillName}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ClipboardCheck className="h-4 w-4 text-primary" aria-hidden="true" />
        <span className="font-medium text-sm">Test Results: {skillName}</span>
        <Badge variant={scoreBadgeVariant(score)}>{score}/10</Badge>
      </div>

      {/* Score bar */}
      <div
        className="w-full h-2 bg-muted rounded-full mb-3"
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-label={`Score: ${score} out of 10`}
      >
        <div
          className={cn('h-full rounded-full transition-all', scoreBarClass(score))}
          style={{ width: `${score * 10}%` }}
        />
      </div>

      {/* Pass/fail checklist */}
      {(passed.length > 0 || failed.length > 0) && (
        <div className="space-y-1 mb-3">
          {passed.map((item, i) => (
            <div key={`pass-${i}`} className="flex items-center gap-2 text-sm">
              <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
          {failed.map((item, i) => (
            <div key={`fail-${i}`} className="flex items-center gap-2 text-sm">
              <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* Suggestions (collapsible) */}
      {suggestions.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="text-sm text-muted-foreground flex items-center gap-1 mb-2 hover:text-foreground transition-colors"
            aria-expanded={isExpanded}
            aria-controls="skill-suggestions-list"
          >
            <ChevronRight
              className={cn('h-3 w-3 transition-transform', isExpanded && 'rotate-90')}
              aria-hidden="true"
            />
            {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}
          </button>
          {isExpanded && (
            <ul id="skill-suggestions-list" className="ml-4 mb-2 space-y-1">
              {suggestions.map((s, i) => (
                <li key={i} className="text-sm text-muted-foreground">
                  - {s}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Refine button */}
      <div className="flex items-center gap-2 mt-2">
        <Button
          size="sm"
          variant="outline"
          onClick={onRefine}
          aria-label="Refine this skill based on test feedback"
        >
          <RefreshCw className="h-3 w-3 mr-1" aria-hidden="true" />
          Refine
        </Button>
      </div>
    </div>
  );
});

SkillTestResultCard.displayName = 'SkillTestResultCard';
