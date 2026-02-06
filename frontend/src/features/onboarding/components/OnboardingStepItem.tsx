'use client';

/**
 * OnboardingStepItem - Individual onboarding step component
 *
 * T022: Create OnboardingStepItem component
 * Source: FR-001, US1
 */
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Check, Key, Users, FileText, ArrowRight, Wand2 } from 'lucide-react';
import type { OnboardingStep } from '@/services/api/onboarding';

export interface OnboardingStepItemProps {
  /** Step identifier */
  step: OnboardingStep;
  /** Step configuration */
  config: {
    title: string;
    description: string;
    actionLabel: string;
    icon: 'key' | 'users' | 'note' | 'wand';
  };
  /** Whether the step is completed */
  completed: boolean;
  /** Whether this step is currently active */
  isActive: boolean;
  /** Whether this is the next suggested step */
  isNext: boolean;
  /** Handler for step action */
  onAction: () => void;
  /** Whether actions are disabled */
  disabled?: boolean;
}

const ICON_MAP = {
  key: Key,
  users: Users,
  note: FileText,
  wand: Wand2,
};

/**
 * OnboardingStepItem - displays a single onboarding step
 *
 * Shows completion state, icon, title, description, and action button.
 * Highlights the next recommended step.
 */
export function OnboardingStepItem({
  config,
  completed,
  isActive,
  isNext,
  onAction,
  disabled,
}: OnboardingStepItemProps) {
  const Icon = ICON_MAP[config.icon];

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg transition-all duration-200',
        'border',
        completed
          ? 'bg-primary/5 border-primary/20'
          : isNext
            ? 'bg-card border-primary/40 shadow-sm'
            : 'bg-card/50 border-border/50',
        isActive && !completed && 'ring-2 ring-primary ring-offset-2'
      )}
    >
      {/* Status indicator */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          'transition-colors duration-200',
          completed
            ? 'bg-primary text-primary-foreground'
            : isNext
              ? 'bg-primary/20 text-primary'
              : 'bg-muted text-muted-foreground'
        )}
      >
        {completed ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className={cn('font-medium text-sm', completed ? 'text-primary' : 'text-foreground')}>
          {config.title}
        </div>
        <div className="text-xs text-muted-foreground truncate">{config.description}</div>
      </div>

      {/* Action */}
      {!completed && (
        <Button
          variant={isNext ? 'default' : 'outline'}
          size="sm"
          onClick={onAction}
          disabled={disabled}
          className={cn(
            'shrink-0',
            isNext && 'animate-in fade-in-0 slide-in-from-right-2 duration-300'
          )}
        >
          {config.actionLabel}
          {isNext && <ArrowRight className="ml-1 h-3 w-3" />}
        </Button>
      )}

      {completed && (
        <span className="text-xs text-primary font-medium px-2 py-1 bg-primary/10 rounded">
          Done
        </span>
      )}
    </div>
  );
}
