/**
 * Avatar Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Warm fallback colors
 * - AI avatar variant for Pilot collaborative partner
 * - Squircle variant for non-user avatars
 */

import * as React from 'react';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { cva, type VariantProps } from 'class-variance-authority';
import { Compass } from 'lucide-react';
import { cn } from '@/lib/utils';

const avatarVariants = cva(
  'relative flex shrink-0 overflow-hidden',
  {
    variants: {
      size: {
        xs: 'h-6 w-6 text-[10px]',
        sm: 'h-8 w-8 text-xs',
        default: 'h-10 w-10 text-sm',
        lg: 'h-12 w-12 text-base',
        xl: 'h-16 w-16 text-lg',
      },
      shape: {
        circle: 'rounded-full',
        squircle: 'rounded-xl',
      },
    },
    defaultVariants: {
      size: 'default',
      shape: 'circle',
    },
  }
);

export interface AvatarProps
  extends React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>,
    VariantProps<typeof avatarVariants> {}

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  AvatarProps
>(({ className, size, shape, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(avatarVariants({ size, shape, className }))}
    {...props}
  />
));
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, alt, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square h-full w-full', className)}
    alt={alt || ''} // Empty alt for decorative, meaningful alt for profile
    {...props}
  />
));
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center bg-muted font-medium',
      className
    )}
    {...props}
  />
));
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

export { Avatar, AvatarImage, AvatarFallback };

/**
 * Generate initials from a name
 */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Generate a warm, consistent color from a string
 */
function stringToWarmColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  // Use warm hues (0-60 = reds/oranges, 300-360 = pinks/magentas)
  // Plus some teals (150-180)
  const hueRanges = [
    [0, 40],     // Red to orange
    [150, 180],  // Teal
    [200, 230],  // Blue
    [320, 360],  // Pink/magenta
  ];
  const rangeIndex = Math.abs(hash) % hueRanges.length;
  const [min, max] = hueRanges[rangeIndex];
  const hue = min + (Math.abs(hash >> 8) % (max - min));
  return `hsl(${hue}, 55%, 50%)`;
}

const statusColors = {
  online: 'bg-state-done',
  offline: 'bg-muted-foreground/50',
  away: 'bg-priority-medium',
  busy: 'bg-destructive',
};

/**
 * UserAvatar Component
 *
 * Convenience wrapper that handles initials generation and status.
 */

export interface UserAvatarProps extends VariantProps<typeof avatarVariants> {
  user: {
    name: string;
    email?: string;
    avatarUrl?: string | null;
  };
  showStatus?: boolean;
  status?: 'online' | 'offline' | 'away' | 'busy';
  className?: string;
}

export function UserAvatar({
  user,
  size,
  shape,
  showStatus,
  status = 'offline',
  className,
}: UserAvatarProps) {
  const initials = getInitials(user.name);
  const fallbackColor = stringToWarmColor(user.email || user.name);

  return (
    <div className={cn('relative inline-flex', className)}>
      <Avatar size={size} shape={shape}>
        {user.avatarUrl && (
          <AvatarImage src={user.avatarUrl} alt={`${user.name}'s avatar`} />
        )}
        <AvatarFallback style={{ backgroundColor: fallbackColor }}>
          <span className="text-white">{initials}</span>
        </AvatarFallback>
      </Avatar>
      {showStatus && (
        <span
          className={cn(
            'absolute bottom-0 right-0 block rounded-full ring-2 ring-background',
            size === 'xs' && 'h-1.5 w-1.5',
            size === 'sm' && 'h-2 w-2',
            (!size || size === 'default') && 'h-2.5 w-2.5',
            size === 'lg' && 'h-3 w-3',
            size === 'xl' && 'h-4 w-4',
            statusColors[status]
          )}
          aria-label={`Status: ${status}`}
        />
      )}
    </div>
  );
}

/**
 * AIAvatar Component
 *
 * Avatar for the AI collaborative partner (Pilot).
 * Uses the compass icon as the avatar.
 */

export interface AIAvatarProps extends VariantProps<typeof avatarVariants> {
  className?: string;
}

export function AIAvatar({ size, className }: AIAvatarProps) {
  const iconSizes = {
    xs: 'h-3 w-3',
    sm: 'h-4 w-4',
    default: 'h-5 w-5',
    lg: 'h-6 w-6',
    xl: 'h-8 w-8',
  };

  return (
    <div
      className={cn(
        avatarVariants({ size, shape: 'squircle' }),
        'bg-ai flex items-center justify-center',
        className
      )}
      aria-label="AI Pilot"
    >
      <Compass
        className={cn('text-ai-foreground', iconSizes[size || 'default'])}
        aria-hidden="true"
      />
    </div>
  );
}

/**
 * AvatarGroup Component
 *
 * Stack of avatars for assignees/collaborators.
 */

export interface AvatarGroupProps {
  users: Array<{
    name: string;
    email?: string;
    avatarUrl?: string | null;
  }>;
  max?: number;
  size?: VariantProps<typeof avatarVariants>['size'];
  className?: string;
  /**
   * Include AI avatar at the end (for AI-assisted content)
   */
  includeAI?: boolean;
}

export function AvatarGroup({
  users,
  max = 4,
  size = 'sm',
  className,
  includeAI,
}: AvatarGroupProps) {
  const effectiveMax = includeAI ? max - 1 : max;
  const visibleUsers = users.slice(0, effectiveMax);
  const remainingCount = users.length - effectiveMax;

  return (
    <div className={cn('flex -space-x-2', className)}>
      {visibleUsers.map((user, index) => (
        <UserAvatar
          key={user.email || index}
          user={user}
          size={size}
          className="ring-2 ring-background"
        />
      ))}
      {remainingCount > 0 && !includeAI && (
        <div
          className={cn(
            avatarVariants({ size, shape: 'circle' }),
            'flex items-center justify-center bg-muted font-medium text-muted-foreground ring-2 ring-background'
          )}
        >
          +{remainingCount}
        </div>
      )}
      {includeAI && (
        <AIAvatar size={size} className="ring-2 ring-background" />
      )}
    </div>
  );
}
