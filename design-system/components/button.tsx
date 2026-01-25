/**
 * Button Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Teal-green primary color
 * - Dusty blue AI collaborative variant
 * - Apple-style squircle corners
 * - Scale + shadow hover interactions
 * - Lucide icons
 */

import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  [
    // Base styles
    'inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium',
    // Squircle corners (Apple-style)
    'rounded-xl',
    // Focus states
    'ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    // Disabled state
    'disabled:pointer-events-none disabled:opacity-50',
    // Touch optimization
    'touch-manipulation select-none',
    // Icon sizing
    '[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
    // Base transition for all variants
    'transition-all duration-normal ease-out',
  ].join(' '),
  {
    variants: {
      variant: {
        // Primary - Teal-green with scale+shadow hover
        default: [
          'bg-primary text-primary-foreground',
          'hover:bg-primary-hover hover:scale-[1.02] hover:shadow-md',
          'active:scale-[0.98]',
        ].join(' '),
        // Destructive - Warm red
        destructive: [
          'bg-destructive text-destructive-foreground',
          'hover:bg-destructive/90 hover:scale-[1.02] hover:shadow-md',
          'active:scale-[0.98]',
        ].join(' '),
        // Outline
        outline: [
          'border border-input bg-background',
          'hover:bg-accent hover:text-accent-foreground hover:scale-[1.02] hover:shadow-sm',
          'active:scale-[0.98]',
        ].join(' '),
        // Secondary
        secondary: [
          'bg-secondary text-secondary-foreground',
          'hover:bg-secondary/80 hover:scale-[1.02]',
          'active:scale-[0.98]',
        ].join(' '),
        // Ghost
        ghost: [
          'hover:bg-accent hover:text-accent-foreground',
          'active:scale-[0.98]',
        ].join(' '),
        // Link
        link: 'text-primary underline-offset-4 hover:underline',
        // AI Collaborative Partner - Dusty blue
        ai: [
          'bg-ai text-ai-foreground',
          'hover:bg-ai/90 hover:scale-[1.02] hover:shadow-md',
          'active:scale-[0.98]',
        ].join(' '),
        // AI Subtle - For secondary AI actions
        'ai-subtle': [
          'bg-ai-muted text-ai border border-ai-border',
          'hover:bg-ai/10 hover:scale-[1.02]',
          'active:scale-[0.98]',
        ].join(' '),
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3 text-xs',
        lg: 'h-11 px-8',
        xl: 'h-12 px-10 text-base',
        icon: 'h-10 w-10',
        'icon-sm': 'h-8 w-8',
        'icon-lg': 'h-12 w-12',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  /**
   * Required for icon-only buttons to ensure accessibility
   */
  'aria-label'?: string;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : 'button';
    const isIconOnly = size === 'icon' || size === 'icon-sm' || size === 'icon-lg';

    // Warn in development if icon-only button lacks aria-label
    if (process.env.NODE_ENV === 'development' && isIconOnly && !props['aria-label']) {
      console.warn(
        'Button: Icon-only buttons require an aria-label for accessibility.'
      );
    }

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading && (
          <Loader2
            className="animate-spin"
            aria-hidden="true"
          />
        )}
        {children}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
