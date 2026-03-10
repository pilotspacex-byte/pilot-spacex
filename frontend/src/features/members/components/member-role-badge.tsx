/**
 * MemberRoleBadge — displays a workspace member's role as a badge.
 *
 * When customRole is set: renders the custom role name with outline style.
 * When customRole is null: renders the built-in WorkspaceRole badge
 * (owner = default, admin = secondary, member/guest = outline).
 *
 * Visual style matches existing role badges in member-card.tsx and member-row.tsx.
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface MemberRoleBadgeProps {
  role: 'owner' | 'admin' | 'member' | 'guest' | null;
  customRole?: { id: string; name: string } | null;
  className?: string;
}

const BUILTIN_ROLE_CONFIG: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'outline' }
> = {
  owner: { label: 'Owner', variant: 'default' },
  admin: { label: 'Admin', variant: 'secondary' },
  member: { label: 'Member', variant: 'outline' },
  guest: { label: 'Guest', variant: 'outline' },
};

export function MemberRoleBadge({ role, customRole, className }: MemberRoleBadgeProps) {
  if (customRole) {
    return (
      <Badge
        variant="outline"
        className={cn('font-normal', className)}
        data-testid="role-badge-custom"
      >
        {customRole.name}
      </Badge>
    );
  }

  if (!role || !BUILTIN_ROLE_CONFIG[role]) return null;

  const { label, variant } = BUILTIN_ROLE_CONFIG[role];
  return (
    <Badge variant={variant} className={className} data-testid={`role-badge-${role}`}>
      {label}
    </Badge>
  );
}
