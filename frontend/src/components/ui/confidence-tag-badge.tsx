/**
 * Confidence Tag Badge Component.
 *
 * Displays AI confidence tags per DD-048:
 * - Recommended: confidence > 0.8 (green)
 * - Default: 0.6-0.8 (blue)
 * - Current: matches existing pattern (gray)
 * - Alternative: < 0.6 (yellow)
 *
 * @module components/ui/confidence-tag-badge
 * @see specs/004-mvp-agents-build/tasks/P20-T154-T164.md#T156
 */

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Star, Check, Minus, HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

type ConfidenceTag = 'recommended' | 'default' | 'current' | 'alternative';

interface ConfidenceTagBadgeProps {
  tag: ConfidenceTag;
  score?: number;
  showScore?: boolean;
  className?: string;
}

const tagConfig = {
  recommended: {
    label: 'Recommended',
    icon: Star,
    className:
      'bg-green-500/10 text-green-600 border-green-200 dark:bg-green-500/20 dark:text-green-400 dark:border-green-800',
    description: 'High confidence - strongly suggested',
  },
  default: {
    label: 'Default',
    icon: Check,
    className:
      'bg-blue-500/10 text-blue-600 border-blue-200 dark:bg-blue-500/20 dark:text-blue-400 dark:border-blue-800',
    description: 'Good confidence - reasonable option',
  },
  current: {
    label: 'Current',
    icon: Minus,
    className: 'bg-muted text-muted-foreground border-border',
    description: 'Moderate confidence - matches existing pattern',
  },
  alternative: {
    label: 'Alternative',
    icon: HelpCircle,
    className: 'bg-muted/60 text-muted-foreground border-border/60',
    description: 'Lower confidence - consider carefully',
  },
};

export function ConfidenceTagBadge({
  tag,
  score,
  showScore = false,
  className,
}: ConfidenceTagBadgeProps) {
  const config = tagConfig[tag];
  const Icon = config.icon;
  const confidencePercent = score !== undefined ? Math.round(score * 100) : undefined;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn('text-xs gap-1 font-normal', config.className, className)}
        >
          <Icon className="h-3 w-3" />
          {config.label}
          {showScore && confidencePercent !== undefined && (
            <span className="opacity-70">({confidencePercent}%)</span>
          )}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        <p className="text-sm">{config.description}</p>
        {confidencePercent !== undefined && (
          <p className="text-xs opacity-70 mt-1">Confidence: {confidencePercent}%</p>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
