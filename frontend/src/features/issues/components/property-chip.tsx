'use client';

/**
 * PropertyChip - Clickable chip for a single issue property.
 *
 * Renders a compact button that opens a Radix Popover with the corresponding
 * selector component (state, priority, assignee, etc.).
 */
import { type ReactNode, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FieldSaveIndicator } from './field-save-indicator';

export interface PropertyChipProps {
  /** Display content (icon + text) */
  children: ReactNode;
  /** Popover content (selector component) */
  popoverContent: ReactNode;
  /** aria-label for the chip */
  label: string;
  /** Field name for save status indicator */
  fieldName?: string;
  /** Disabled state */
  disabled?: boolean;
  /** Additional class name */
  className?: string;
  /** Popover alignment */
  align?: 'start' | 'center' | 'end';
  /** Popover width */
  popoverWidth?: string;
}

export function PropertyChip({
  children,
  popoverContent,
  label,
  fieldName,
  disabled = false,
  className,
  align = 'start',
  popoverWidth = 'w-56',
}: PropertyChipProps) {
  const [open, setOpen] = useState(false);

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!disabled) setOpen(next);
    },
    [disabled]
  );

  return (
    <div className="flex items-center gap-0.5">
      <Popover open={open} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <button
            type="button"
            role="button"
            aria-label={label}
            aria-haspopup="listbox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              'inline-flex items-center gap-1 rounded-[6px] px-1.5 py-0.5 text-xs',
              'transition-colors duration-100',
              'cursor-pointer select-none',
              'hover:bg-muted/50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              open && 'bg-background ring-1 ring-primary/30 shadow-sm',
              disabled && 'cursor-default opacity-60',
              className
            )}
          >
            {children}
          </button>
        </PopoverTrigger>
        <PopoverContent className={cn('p-2', popoverWidth)} align={align} sideOffset={4}>
          {popoverContent}
        </PopoverContent>
      </Popover>
      {fieldName && <FieldSaveIndicator fieldName={fieldName} />}
    </div>
  );
}
