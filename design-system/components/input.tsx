/**
 * Input Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Apple-style squircle corners
 * - Warm off-white backgrounds
 * - Proper focus states with teal ring
 * - AI suggestion variant
 */

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const inputVariants = cva(
  [
    // Base layout
    'flex h-10 w-full px-3 py-2',
    // Squircle corners
    'rounded-xl',
    // Colors
    'border border-input bg-background text-sm',
    // Ring offset
    'ring-offset-background',
    // File input
    'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground',
    // Placeholder
    'placeholder:text-muted-foreground',
    // Focus state with teal ring
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    // Disabled
    'disabled:cursor-not-allowed disabled:opacity-50',
    // Touch optimization
    'touch-manipulation',
    // Transition
    'transition-all duration-fast ease-out',
  ].join(' '),
  {
    variants: {
      variant: {
        default: '',
        error: 'border-destructive focus-visible:ring-destructive',
        ai: 'border-ai bg-ai-muted/30 focus-visible:ring-ai',
      },
      inputSize: {
        default: 'h-10',
        sm: 'h-9 text-xs',
        lg: 'h-11',
      },
    },
    defaultVariants: {
      variant: 'default',
      inputSize: 'default',
    },
  }
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'>,
    VariantProps<typeof inputVariants> {
  /**
   * Error message to display below the input
   */
  error?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, variant, inputSize, error, ...props }, ref) => {
    // Auto-disable spellcheck for specific input types
    const shouldDisableSpellcheck =
      type === 'email' || type === 'password' || props.name?.includes('code');

    return (
      <input
        type={type}
        className={cn(
          inputVariants({ variant: error ? 'error' : variant, inputSize, className })
        )}
        ref={ref}
        spellCheck={shouldDisableSpellcheck ? false : props.spellCheck}
        // Never prevent paste - this is an accessibility violation
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input, inputVariants };

/**
 * Textarea Component
 *
 * Multi-line text input with same styling as Input.
 */

const textareaVariants = cva(
  [
    // Base layout
    'flex min-h-[80px] w-full px-3 py-2',
    // Squircle corners
    'rounded-xl',
    // Colors
    'border border-input bg-background text-sm',
    // Ring offset
    'ring-offset-background',
    // Placeholder
    'placeholder:text-muted-foreground',
    // Focus state
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    // Disabled
    'disabled:cursor-not-allowed disabled:opacity-50',
    // Transition
    'transition-all duration-fast ease-out',
  ].join(' '),
  {
    variants: {
      variant: {
        default: '',
        error: 'border-destructive focus-visible:ring-destructive',
        ai: 'border-ai bg-ai-muted/30 focus-visible:ring-ai',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {
  error?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, error, ...props }, ref) => {
    return (
      <textarea
        className={cn(textareaVariants({ variant: error ? 'error' : variant, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = 'Textarea';

export { Textarea, textareaVariants };

/**
 * FormField Component
 *
 * Wraps input with label and error message for proper accessibility:
 * - Clickable labels via htmlFor
 * - Error messages linked with aria-describedby
 * - aria-invalid for screen readers
 */

export interface FormFieldProps {
  id: string;
  label: string;
  error?: string;
  description?: string;
  required?: boolean;
  children: React.ReactElement<InputProps | TextareaProps>;
}

export function FormField({
  id,
  label,
  error,
  description,
  required,
  children,
}: FormFieldProps) {
  const errorId = `${id}-error`;
  const descriptionId = `${id}-description`;

  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
      >
        {label}
        {required && (
          <span className="ml-1 text-destructive" aria-hidden="true">
            *
          </span>
        )}
      </label>

      {description && (
        <p id={descriptionId} className="text-sm text-muted-foreground">
          {description}
        </p>
      )}

      {React.cloneElement(children, {
        id,
        'aria-invalid': error ? true : undefined,
        'aria-describedby': [
          error ? errorId : null,
          description ? descriptionId : null,
        ]
          .filter(Boolean)
          .join(' ') || undefined,
        error,
      })}

      {error && (
        <p
          id={errorId}
          className="text-sm text-destructive"
          role="alert"
          aria-live="polite"
        >
          {error}
        </p>
      )}
    </div>
  );
}
