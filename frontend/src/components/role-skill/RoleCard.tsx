'use client';

/**
 * RoleCard - Interactive card for SDLC role selection.
 *
 * Used in onboarding role selection grid (Screen 1) and profile settings
 * default role selector (Screen 6). Supports selected/unselected states,
 * primary designation, and badge indicators.
 *
 * T019: Create RoleCard component
 * Source: FR-001, FR-002, FR-011, US1, US4
 */

import React, { useCallback } from 'react';
import { Check, Star, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getRoleIcon } from './role-icons';

export interface RoleCardProps {
  /** Role type identifier (used as key, not displayed). */
  roleType: string;
  /** Human-readable role name. */
  displayName: string;
  /** Brief description of the role. */
  description: string;
  /** Lucide icon identifier from backend template. */
  icon: string;
  /** Whether this card is currently selected. */
  selected?: boolean;
  /** Selection order number (1, 2, 3) when selected; null if unselected. */
  selectionOrder?: number | null;
  /** Whether this is the primary (first-selected) role. */
  isPrimary?: boolean;
  /** Show "Your default" badge (user's profile default role). */
  isDefaultRole?: boolean;
  /** Show "Suggested by owner" badge (workspace owner hint). */
  isSuggestedByOwner?: boolean;
  /** Prevent interaction. */
  disabled?: boolean;
  /** Called when the card is toggled. */
  onToggle?: () => void;
  /** Size variant: standard (160x140) for onboarding, compact (120x100) for profile. */
  variant?: 'standard' | 'compact';
}

const ORDER_LABELS = ['\u2460', '\u2461', '\u2462'] as const; // ①②③

export function RoleCard({
  roleType,
  displayName,
  description,
  icon,
  selected = false,
  selectionOrder = null,
  isPrimary = false,
  isDefaultRole = false,
  isSuggestedByOwner = false,
  disabled = false,
  onToggle,
  variant = 'standard',
}: RoleCardProps) {
  const isCompact = variant === 'compact';

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (disabled) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onToggle?.();
      }
    },
    [disabled, onToggle]
  );

  const handleClick = useCallback(() => {
    if (disabled) return;
    onToggle?.();
  }, [disabled, onToggle]);

  return (
    <div
      role="checkbox"
      aria-checked={selected}
      aria-label={`${displayName}${isPrimary ? ', primary role' : ''}${isDefaultRole ? ', your default role' : ''}${isSuggestedByOwner ? ', suggested by workspace owner' : ''}`}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      data-testid={`role-card-${roleType}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        // Base
        'relative flex flex-col items-center justify-center gap-1.5 rounded-xl border text-center',
        'cursor-pointer select-none outline-none',
        // Focus ring
        'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
        // Motion-safe hover
        'motion-safe:transition-all motion-safe:duration-200',
        'motion-reduce:transition-none',
        // Size
        isCompact ? 'h-[100px] w-[120px] p-2' : 'h-[140px] w-[160px] p-3',
        // States
        selected
          ? 'border-2 border-primary bg-primary/5'
          : 'border border-border bg-[#F7F5F2] hover:-translate-y-0.5 hover:shadow-md',
        // Disabled
        disabled && 'pointer-events-none opacity-50'
      )}
    >
      {/* Selection checkmark — top left */}
      {selected && (
        <div
          className="absolute left-2 top-2 flex h-4 w-4 items-center justify-center rounded-full bg-primary"
          aria-hidden="true"
        >
          <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
        </div>
      )}

      {/* Selection order badge — top right */}
      {selected && selectionOrder != null && selectionOrder >= 1 && selectionOrder <= 3 && (
        <span
          className="absolute right-2 top-2 text-xs font-semibold text-primary"
          aria-hidden="true"
        >
          {ORDER_LABELS[selectionOrder - 1]}
        </span>
      )}

      {/* Icon */}
      {React.createElement(getRoleIcon(icon), {
        className: cn(
          'shrink-0',
          isCompact ? 'h-5 w-5' : 'h-6 w-6',
          selected ? 'text-primary' : 'text-muted-foreground'
        ),
        'aria-hidden': true,
      })}

      {/* Name */}
      <span
        className={cn(
          'font-semibold leading-tight',
          isCompact ? 'text-xs' : 'text-sm',
          selected ? 'text-foreground' : 'text-foreground'
        )}
      >
        {displayName}
      </span>

      {/* PRIMARY label */}
      {isPrimary && selected && (
        <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">
          Primary
        </span>
      )}

      {/* Description (standard only, hidden when primary label shown) */}
      {!isCompact && !(isPrimary && selected) && (
        <span className="line-clamp-2 text-xs leading-tight text-muted-foreground">
          {description}
        </span>
      )}

      {/* Badges */}
      {(isDefaultRole || isSuggestedByOwner) && (
        <div className="absolute inset-x-0 bottom-1.5 flex justify-center">
          {isDefaultRole && (
            <span className="inline-flex items-center gap-0.5 rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
              <Star className="h-2.5 w-2.5" aria-hidden="true" />
              Your default
            </span>
          )}
          {isSuggestedByOwner && !isDefaultRole && (
            <span className="inline-flex items-center gap-0.5 rounded-md bg-[#6B8FAD]/10 px-1.5 py-0.5 text-[10px] font-medium text-[#6B8FAD]">
              <User className="h-2.5 w-2.5" aria-hidden="true" />
              Suggested by owner
            </span>
          )}
        </div>
      )}
    </div>
  );
}
