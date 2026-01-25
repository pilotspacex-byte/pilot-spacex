/**
 * Card Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Apple-style squircle corners
 * - Scale + shadow hover interactions
 * - Soft tinted shadows
 * - AI collaborative partner variant
 * - Frosted glass effect option
 */

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const cardVariants = cva(
  [
    // Squircle corners
    'rounded-2xl',
    // Base styling
    'bg-card text-card-foreground',
    // Border
    'border border-border',
  ].join(' '),
  {
    variants: {
      variant: {
        // Default with soft shadow
        default: 'shadow-sm',
        // Outline only
        outline: 'border-2 shadow-none',
        // Ghost - no border or shadow
        ghost: 'border-transparent shadow-none bg-transparent',
        // Interactive - scale + shadow on hover
        interactive: [
          'shadow-sm cursor-pointer',
          'transition-all duration-normal ease-out',
          'hover:scale-[1.02] hover:shadow-elevated',
          'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
          'active:scale-[0.99]',
        ].join(' '),
        // Elevated - stronger shadow
        elevated: 'shadow-elevated',
        // AI Collaborative Partner - dusty blue accent
        ai: [
          'border-l-4 border-l-ai bg-ai-muted/30',
          'shadow-sm',
        ].join(' '),
        // AI Interactive
        'ai-interactive': [
          'border-l-4 border-l-ai bg-ai-muted/30',
          'shadow-sm cursor-pointer',
          'transition-all duration-normal ease-out',
          'hover:scale-[1.02] hover:shadow-elevated hover:bg-ai-muted/50',
          'focus-within:ring-2 focus-within:ring-ai focus-within:ring-offset-2',
          'active:scale-[0.99]',
        ].join(' '),
        // Frosted glass effect
        frosted: [
          'bg-background/80 backdrop-blur-md',
          'border-white/20',
          'shadow-lg',
        ].join(' '),
      },
      padding: {
        none: '',
        sm: 'p-3',
        default: 'p-4',
        lg: 'p-6',
        xl: 'p-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'default',
    },
  }
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding, className }))}
      {...props}
    />
  )
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5', className)}
    {...props}
  />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      'text-lg font-semibold leading-none tracking-tight text-balance',
      className
    )}
    {...props}
  />
));
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('', className)} {...props} />
));
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center pt-4', className)}
    {...props}
  />
));
CardFooter.displayName = 'CardFooter';

/**
 * AICard Component
 *
 * Specialized card for AI-generated or AI-suggested content.
 * Includes visual indicators and collaborative attribution.
 */

export interface AICardProps extends CardProps {
  /**
   * Show AI indicator in header
   */
  showIndicator?: boolean;
}

const AICard = React.forwardRef<HTMLDivElement, AICardProps>(
  ({ className, showIndicator = true, children, ...props }, ref) => (
    <Card
      ref={ref}
      variant="ai"
      className={cn(className)}
      {...props}
    >
      {children}
    </Card>
  )
);
AICard.displayName = 'AICard';

/**
 * IssueCard Component
 *
 * Specialized card for displaying issues in board/list views.
 * Interactive with scale + shadow hover.
 */

export interface IssueCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Whether the card is being dragged
   */
  isDragging?: boolean;
  /**
   * Whether this is an AI-generated issue
   */
  isAIGenerated?: boolean;
}

const IssueCard = React.forwardRef<HTMLDivElement, IssueCardProps>(
  ({ className, isDragging, isAIGenerated, ...props }, ref) => (
    <Card
      ref={ref}
      variant={isAIGenerated ? 'ai-interactive' : 'interactive'}
      padding="sm"
      className={cn(
        // Drag state
        isDragging && 'rotate-2 scale-105 opacity-90 shadow-lg',
        className
      )}
      {...props}
    />
  )
);
IssueCard.displayName = 'IssueCard';

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  AICard,
  IssueCard,
  cardVariants,
};
