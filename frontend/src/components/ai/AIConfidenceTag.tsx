'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Sparkles, Check, Minus, CircleDot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

/**
 * AI Confidence Tag variants per DD-048:
 * - recommended: High confidence (>0.8), green - AI strongly recommends
 * - default: Medium confidence (0.6-0.8), blue - AI's default suggestion
 * - current: What's currently set, gray outline - No change suggested
 * - alternative: Lower confidence (<0.6), gray - Possible alternatives
 */
const confidenceTagVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        recommended:
          'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 dark:bg-emerald-500/20 dark:text-emerald-400',
        default:
          'bg-blue-500/10 text-blue-600 border border-blue-500/20 dark:bg-blue-500/20 dark:text-blue-400',
        current: 'bg-muted text-muted-foreground border border-border',
        alternative: 'bg-muted/60 text-muted-foreground border border-border/60',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export type ConfidenceLevel = 'recommended' | 'default' | 'current' | 'alternative';

export interface AIConfidenceTagProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof confidenceTagVariants> {
  /** Confidence score (0-1), determines variant if not explicitly set */
  confidence?: number;
  /** Show sparkle icon */
  showIcon?: boolean;
  /** Tooltip text explaining the confidence level */
  tooltip?: string;
  /** Whether this is the currently selected option */
  isCurrent?: boolean;
}

/**
 * Derives confidence level from numeric score.
 * @param confidence - Score between 0 and 1
 * @param isCurrent - Whether this is the current value
 */
export function getConfidenceLevel(confidence: number, isCurrent = false): ConfidenceLevel {
  if (isCurrent) return 'current';
  if (confidence >= 0.8) return 'recommended';
  if (confidence >= 0.6) return 'default';
  return 'alternative';
}

/**
 * Get tooltip text for confidence level.
 */
function getDefaultTooltip(variant: ConfidenceLevel, confidence?: number): string {
  const confidenceText = confidence !== undefined ? ` (${Math.round(confidence * 100)}%)` : '';
  switch (variant) {
    case 'recommended':
      return `AI strongly recommends this option${confidenceText}`;
    case 'default':
      return `AI suggests this as a good option${confidenceText}`;
    case 'current':
      return 'Currently selected value';
    case 'alternative':
      return `Alternative option to consider${confidenceText}`;
  }
}

/**
 * Get icon for confidence level.
 */
function getIcon(variant: ConfidenceLevel) {
  switch (variant) {
    case 'recommended':
      return <Sparkles className="size-3" />;
    case 'default':
      return <Check className="size-3" />;
    case 'current':
      return <CircleDot className="size-3" />;
    case 'alternative':
      return <Minus className="size-3" />;
  }
}

/**
 * AIConfidenceTag displays AI suggestion confidence levels.
 *
 * Uses a color-coded system per DD-048:
 * - Green (recommended): High confidence >80%
 * - Blue (default): Medium confidence 60-80%
 * - Gray outline (current): Currently selected
 * - Gray filled (alternative): Lower confidence <60%
 *
 * @example
 * ```tsx
 * <AIConfidenceTag confidence={0.92} showIcon />
 * <AIConfidenceTag variant="recommended">Recommended</AIConfidenceTag>
 * <AIConfidenceTag variant="current" isCurrent>Current</AIConfidenceTag>
 * ```
 */
export function AIConfidenceTag({
  className,
  variant,
  confidence,
  showIcon = false,
  tooltip,
  isCurrent = false,
  children,
  ...props
}: AIConfidenceTagProps) {
  // Derive variant from confidence if not explicitly set
  const derivedVariant =
    variant ?? (confidence !== undefined ? getConfidenceLevel(confidence, isCurrent) : 'default');

  const tooltipText = tooltip ?? getDefaultTooltip(derivedVariant, confidence);

  const tag = (
    <span className={cn(confidenceTagVariants({ variant: derivedVariant }), className)} {...props}>
      {showIcon && getIcon(derivedVariant)}
      {children}
      {confidence !== undefined && !children && <span>{Math.round(confidence * 100)}%</span>}
    </span>
  );

  if (tooltip !== undefined || confidence !== undefined) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{tag}</TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <p className="text-xs">{tooltipText}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return tag;
}

export { confidenceTagVariants };
