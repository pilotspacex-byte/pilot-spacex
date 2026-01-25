/**
 * Toast/Notification Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Apple-style squircle corners
 * - Warm color variants
 * - Lucide icons
 * - AI notification variant
 */

import * as React from 'react';
import * as ToastPrimitive from '@radix-ui/react-toast';
import { cva, type VariantProps } from 'class-variance-authority';
import { X, Check, AlertTriangle, Info, Compass } from 'lucide-react';
import { cn } from '@/lib/utils';

const ToastProvider = ToastPrimitive.Provider;

const ToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Viewport
    ref={ref}
    className={cn(
      'fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4',
      'sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]',
      // Safe area padding for mobile
      'safe-padding-bottom',
      className
    )}
    {...props}
  />
));
ToastViewport.displayName = ToastPrimitive.Viewport.displayName;

const toastVariants = cva(
  [
    // Base
    'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden p-6 pr-8',
    // Squircle corners
    'rounded-2xl',
    // Border and shadow
    'border shadow-elevated',
    // Transitions
    'transition-all data-[swipe=cancel]:translate-x-0',
    'data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)]',
    'data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)]',
    'data-[swipe=move]:transition-none',
    // Animations
    'data-[state=open]:animate-in data-[state=closed]:animate-out',
    'data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full',
    'data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full',
  ].join(' '),
  {
    variants: {
      variant: {
        default: 'border bg-background text-foreground',
        success: 'border-state-done/30 bg-state-done/10 text-state-done',
        warning: 'border-priority-medium/30 bg-priority-medium/10 text-priority-medium',
        error: 'border-destructive/30 bg-destructive/10 text-destructive',
        info: 'border-state-todo/30 bg-state-todo/10 text-state-todo',
        ai: 'border-ai/30 bg-ai-muted text-ai',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

const Toast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Root> &
    VariantProps<typeof toastVariants>
>(({ className, variant, ...props }, ref) => {
  return (
    <ToastPrimitive.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  );
});
Toast.displayName = ToastPrimitive.Root.displayName;

const ToastAction = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Action>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Action>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Action
    ref={ref}
    className={cn(
      'inline-flex h-8 shrink-0 items-center justify-center px-3',
      'rounded-xl border bg-transparent text-sm font-medium',
      'ring-offset-background transition-all duration-fast',
      'hover:bg-secondary hover:scale-[1.02]',
      'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
      'disabled:pointer-events-none disabled:opacity-50',
      'group-[.destructive]:border-muted/40 group-[.destructive]:hover:border-destructive/30',
      'group-[.destructive]:hover:bg-destructive group-[.destructive]:hover:text-destructive-foreground',
      'group-[.destructive]:focus:ring-destructive',
      className
    )}
    {...props}
  />
));
ToastAction.displayName = ToastPrimitive.Action.displayName;

const ToastClose = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Close>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Close
    ref={ref}
    className={cn(
      'absolute right-2 top-2 rounded-lg p-1 text-foreground/50 opacity-0 transition-all duration-fast',
      'hover:text-foreground hover:bg-accent focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100',
      'group-[.destructive]:text-red-300 group-[.destructive]:hover:text-red-50',
      'group-[.destructive]:focus:ring-red-400 group-[.destructive]:focus:ring-offset-red-600',
      className
    )}
    toast-close=""
    aria-label="Close notification"
    {...props}
  >
    <X className="h-4 w-4" aria-hidden="true" />
  </ToastPrimitive.Close>
));
ToastClose.displayName = ToastPrimitive.Close.displayName;

const ToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Title
    ref={ref}
    className={cn('text-sm font-semibold', className)}
    {...props}
  />
));
ToastTitle.displayName = ToastPrimitive.Title.displayName;

const ToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitive.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitive.Description
    ref={ref}
    className={cn('text-sm opacity-90', className)}
    {...props}
  />
));
ToastDescription.displayName = ToastPrimitive.Description.displayName;

type ToastProps = React.ComponentPropsWithoutRef<typeof Toast>;
type ToastActionElement = React.ReactElement<typeof ToastAction>;

export {
  type ToastProps,
  type ToastActionElement,
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
};

/**
 * Toast Icon Helper
 *
 * Returns appropriate icon for toast variant
 */
const toastIcons = {
  default: null,
  success: Check,
  warning: AlertTriangle,
  error: X,
  info: Info,
  ai: Compass,
};

export function getToastIcon(variant: keyof typeof toastIcons) {
  return toastIcons[variant];
}

/**
 * ToastWithIcon Component
 *
 * Toast with appropriate icon based on variant
 */
export interface ToastWithIconProps extends ToastProps {
  title: string;
  description?: string;
}

export function ToastWithIcon({
  variant = 'default',
  title,
  description,
  children,
  ...props
}: ToastWithIconProps) {
  const Icon = getToastIcon(variant as keyof typeof toastIcons);

  return (
    <Toast variant={variant} {...props}>
      <div className="flex items-start gap-3">
        {Icon && (
          <Icon className="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
        )}
        <div className="grid gap-1">
          <ToastTitle>{title}</ToastTitle>
          {description && <ToastDescription>{description}</ToastDescription>}
        </div>
      </div>
      {children}
      <ToastClose />
    </Toast>
  );
}
