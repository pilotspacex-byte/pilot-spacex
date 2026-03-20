'use client';

/**
 * SDLCSuggestionCards — Actionable AI suggestion cards with severity badges.
 *
 * Renders compact cards for sprint completion predictions, stale alerts,
 * and actionable suggestions in the AI Insights section.
 */

import { Lightbulb, AlertTriangle, TrendingUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { SuggestionCardData } from '../types';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const TYPE_CONFIG: Record<SuggestionCardData['type'], { icon: LucideIcon; iconClass: string }> = {
  sprint_completion: { icon: TrendingUp, iconClass: 'text-primary' },
  stale_alert: { icon: AlertTriangle, iconClass: 'text-amber-500' },
  actionable_suggestion: { icon: Lightbulb, iconClass: 'text-blue-500' },
};

const SEVERITY_STYLES: Record<SuggestionCardData['severity'], string> = {
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface SDLCSuggestionCardsProps {
  suggestions: SuggestionCardData[];
  onAction?: (suggestion: SuggestionCardData) => void;
  className?: string;
}

export function SDLCSuggestionCards({
  suggestions,
  onAction,
  className,
}: SDLCSuggestionCardsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className={cn('space-y-2', className)}>
      {suggestions.map((card) => {
        const config = TYPE_CONFIG[card.type];
        const Icon = config.icon;

        return (
          <div
            key={card.id}
            className={cn(
              'flex items-start gap-2.5 rounded-lg border border-border-subtle px-3 py-2.5',
              'motion-safe:transition-colors hover:bg-gray-50/50'
            )}
          >
            <Icon
              className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', config.iconClass)}
              aria-hidden="true"
            />

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">{card.title}</span>
                <Badge
                  className={cn(
                    'px-1.5 py-0 text-[10px] font-medium',
                    SEVERITY_STYLES[card.severity]
                  )}
                >
                  {card.severity}
                </Badge>
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
                {card.description}
              </p>
            </div>

            {card.actionLabel && onAction && (
              <Button
                variant="ghost"
                size="sm"
                className="shrink-0 text-xs text-primary"
                onClick={() => onAction(card)}
              >
                {card.actionLabel}
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
