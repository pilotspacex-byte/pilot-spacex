'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

/* -----------------------------------------------------------------------------
 * Dots Loader
 * -------------------------------------------------------------------------- */

const dotsLoaderVariants = cva('flex items-center gap-1', {
  variants: {
    size: {
      sm: 'gap-0.5',
      md: 'gap-1',
      lg: 'gap-1.5',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

const dotVariants = cva('rounded-full bg-current animate-bounce', {
  variants: {
    size: {
      sm: 'size-1',
      md: 'size-1.5',
      lg: 'size-2',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

export interface DotsLoaderProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof dotsLoaderVariants> {
  /** Number of dots */
  count?: number;
}

const DotsLoader = React.forwardRef<HTMLDivElement, DotsLoaderProps>(
  ({ className, size = 'md', count = 3, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(dotsLoaderVariants({ size }), className)}
        role="status"
        aria-label="Loading"
        {...props}
      >
        {Array.from({ length: count }).map((_, i) => (
          <span
            key={i}
            className={cn(dotVariants({ size }))}
            style={{
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
        <span className="sr-only">Loading...</span>
      </div>
    );
  }
);
DotsLoader.displayName = 'DotsLoader';

/* -----------------------------------------------------------------------------
 * Shimmer Loader
 * -------------------------------------------------------------------------- */

const shimmerLoaderVariants = cva(
  'relative overflow-hidden rounded bg-muted before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent',
  {
    variants: {
      size: {
        sm: 'h-4',
        md: 'h-6',
        lg: 'h-8',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

export interface ShimmerLoaderProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof shimmerLoaderVariants> {}

const ShimmerLoader = React.forwardRef<HTMLDivElement, ShimmerLoaderProps>(
  ({ className, size = 'md', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(shimmerLoaderVariants({ size }), className)}
        role="status"
        aria-label="Loading"
        {...props}
      >
        <span className="sr-only">Loading...</span>
      </div>
    );
  }
);
ShimmerLoader.displayName = 'ShimmerLoader';

/* -----------------------------------------------------------------------------
 * Pulse Loader
 * -------------------------------------------------------------------------- */

const pulseLoaderVariants = cva('rounded bg-muted animate-pulse', {
  variants: {
    size: {
      sm: 'h-4',
      md: 'h-6',
      lg: 'h-8',
    },
  },
  defaultVariants: {
    size: 'md',
  },
});

export interface PulseLoaderProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof pulseLoaderVariants> {}

const PulseLoader = React.forwardRef<HTMLDivElement, PulseLoaderProps>(
  ({ className, size = 'md', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(pulseLoaderVariants({ size }), className)}
        role="status"
        aria-label="Loading"
        {...props}
      >
        <span className="sr-only">Loading...</span>
      </div>
    );
  }
);
PulseLoader.displayName = 'PulseLoader';

/* -----------------------------------------------------------------------------
 * Typing Indicator
 * -------------------------------------------------------------------------- */

export interface TypingIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Who is typing */
  name?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

const TypingIndicator = React.forwardRef<HTMLDivElement, TypingIndicatorProps>(
  ({ className, name = 'AI', size = 'md', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('flex items-center gap-2 text-muted-foreground', className)}
        role="status"
        aria-label={`${name} is typing`}
        {...props}
      >
        <span className="text-sm">{name} is typing</span>
        <DotsLoader size={size} />
      </div>
    );
  }
);
TypingIndicator.displayName = 'TypingIndicator';

/* -----------------------------------------------------------------------------
 * Streaming Cursor
 * -------------------------------------------------------------------------- */

export type StreamingCursorProps = React.HTMLAttributes<HTMLSpanElement>;

/**
 * Blinking cursor for streaming text
 */
const StreamingCursor = React.forwardRef<HTMLSpanElement, StreamingCursorProps>(
  ({ className, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn('ml-0.5 inline-block h-4 w-0.5 animate-blink bg-foreground', className)}
        aria-hidden="true"
        {...props}
      />
    );
  }
);
StreamingCursor.displayName = 'StreamingCursor';

/* -----------------------------------------------------------------------------
 * Exports
 * -------------------------------------------------------------------------- */

export {
  DotsLoader,
  ShimmerLoader,
  PulseLoader,
  TypingIndicator,
  StreamingCursor,
  dotsLoaderVariants,
  shimmerLoaderVariants,
  pulseLoaderVariants,
};
