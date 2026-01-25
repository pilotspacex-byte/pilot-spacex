/**
 * Badge Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Softened semantic colors
 * - Dusty blue AI collaborative partner badges
 * - "You + AI" attribution style
 * - Pilot icon for AI branding
 * - Lucide icons
 */

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Compass, Sparkles, Lightbulb, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  [
    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
    'transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  ].join(' '),
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground',
        secondary:
          'border-transparent bg-secondary text-secondary-foreground',
        destructive:
          'border-transparent bg-destructive text-destructive-foreground',
        outline: 'text-foreground border-border',

        // Issue state variants (softened palette)
        backlog:
          'border-transparent bg-state-backlog/15 text-state-backlog',
        todo: 'border-transparent bg-state-todo/15 text-state-todo',
        'in-progress':
          'border-transparent bg-state-in-progress/15 text-state-in-progress',
        'in-review':
          'border-transparent bg-state-in-review/15 text-state-in-review',
        done: 'border-transparent bg-state-done/15 text-state-done',
        cancelled:
          'border-transparent bg-state-cancelled/15 text-state-cancelled line-through',

        // Priority variants (warm palette)
        'priority-urgent':
          'border-transparent bg-priority-urgent/15 text-priority-urgent',
        'priority-high':
          'border-transparent bg-priority-high/15 text-priority-high',
        'priority-medium':
          'border-transparent bg-priority-medium/15 text-priority-medium',
        'priority-low':
          'border-transparent bg-priority-low/15 text-priority-low',
        'priority-none':
          'border-transparent bg-muted text-muted-foreground',

        // AI Collaborative Partner (dusty blue)
        ai: 'border-ai-border bg-ai-muted text-ai',
        'ai-solid': 'border-transparent bg-ai text-ai-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };

/**
 * PilotIcon Component
 *
 * The AI collaborative partner avatar - a compass/north star symbol
 * representing guidance and navigation through the development process.
 */

export interface PilotIconProps extends React.SVGAttributes<SVGElement> {
  size?: 'sm' | 'md' | 'lg';
}

export function PilotIcon({ size = 'md', className, ...props }: PilotIconProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <Compass
      className={cn(sizeClasses[size], 'text-ai', className)}
      {...props}
    />
  );
}

/**
 * AIBadge Component
 *
 * Badge for AI-generated or AI-suggested content.
 * Uses "You + AI" collaborative attribution style per design spec.
 */

export interface AIBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Type of AI indicator
   */
  type?: 'suggestion' | 'generated' | 'collaborative';
  /**
   * Confidence level (0-100)
   */
  confidence?: number;
  /**
   * Show pilot icon
   */
  showIcon?: boolean;
}

export function AIBadge({
  className,
  type = 'suggestion',
  confidence,
  showIcon = true,
  children,
  ...props
}: AIBadgeProps) {
  const confidenceVariant =
    confidence !== undefined
      ? confidence >= 80
        ? 'high'
        : confidence >= 50
          ? 'medium'
          : 'low'
      : null;

  const Icon = type === 'suggestion' ? Lightbulb : type === 'generated' ? Sparkles : Compass;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        'bg-ai-muted text-ai border border-ai-border',
        className
      )}
      {...props}
    >
      {showIcon && (
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      )}
      {children}
      {confidenceVariant && (
        <span
          className={cn(
            'ml-0.5 rounded px-1 py-0.5 text-[10px] font-semibold',
            confidenceVariant === 'high' &&
              'bg-ai-confidence-high/20 text-ai-confidence-high',
            confidenceVariant === 'medium' &&
              'bg-ai-confidence-medium/20 text-ai-confidence-medium',
            confidenceVariant === 'low' &&
              'bg-ai-confidence-low/20 text-ai-confidence-low'
          )}
          aria-label={`${confidence}% confidence`}
        >
          {confidence}%
        </span>
      )}
    </div>
  );
}

/**
 * AIAttribution Component
 *
 * Shows "You + AI" collaborative attribution for content
 * created with AI assistance.
 */

export interface AIAttributionProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * The human contributor (defaults to "You")
   */
  human?: string;
  /**
   * Show the full "Created with AI" text or just the icon
   */
  compact?: boolean;
}

export function AIAttribution({
  className,
  human = 'You',
  compact = false,
  ...props
}: AIAttributionProps) {
  if (compact) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1 text-xs text-muted-foreground',
          className
        )}
        title={`${human} + AI`}
        {...props}
      >
        <PilotIcon size="sm" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 text-xs text-muted-foreground',
        className
      )}
      {...props}
    >
      <span>{human}</span>
      <span className="text-muted-foreground/60">+</span>
      <PilotIcon size="sm" />
      <span className="text-ai">AI</span>
    </div>
  );
}

/**
 * LabelBadge Component
 *
 * Custom-colored badge for user-defined labels.
 */

export interface LabelBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Label color in HSL format or hex
   */
  color: string;
}

export function LabelBadge({
  className,
  color,
  children,
  ...props
}: LabelBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        className
      )}
      style={{
        backgroundColor: `${color}20`, // 12.5% opacity
        color: color,
        borderColor: `${color}40`, // 25% opacity
      }}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * ConfidenceIndicator Component
 *
 * Visual indicator for AI confidence levels.
 */

export interface ConfidenceIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Confidence level (0-100)
   */
  confidence: number;
  /**
   * Show numeric percentage
   */
  showValue?: boolean;
}

export function ConfidenceIndicator({
  className,
  confidence,
  showValue = true,
  ...props
}: ConfidenceIndicatorProps) {
  const variant = confidence >= 80 ? 'high' : confidence >= 50 ? 'medium' : 'low';
  const Icon = variant === 'high' ? Check : variant === 'low' ? AlertCircle : null;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 text-xs font-medium',
        variant === 'high' && 'text-ai-confidence-high',
        variant === 'medium' && 'text-ai-confidence-medium',
        variant === 'low' && 'text-ai-confidence-low',
        className
      )}
      {...props}
    >
      {Icon && <Icon className="h-3 w-3" aria-hidden="true" />}
      {showValue && <span>{confidence}%</span>}
    </div>
  );
}
