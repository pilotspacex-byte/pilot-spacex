/**
 * MemberCard - Card component for displaying a workspace member in a grid.
 *
 * Vertical layout: role badge, avatar, name, email, meta row.
 * Admin-only actions dropdown with role change sub-menu.
 */

'use client';

import { Crown, Loader2, MoreHorizontal, Shield, ShieldAlert, Trash2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { WorkspaceMember } from '@/features/issues/hooks/use-workspace-members';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { getInitials, formatJoinDate } from '@/features/members/utils/member-utils';
import { cn } from '@/lib/utils';
import { MemberRoleBadge } from './member-role-badge';

interface MemberCardProps {
  member: WorkspaceMember;
  currentUserRole: WorkspaceRole | null;
  isCurrentUser: boolean;
  isLastAdmin?: boolean;
  onRoleChange: (userId: string, role: WorkspaceRole) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
  onAvailabilityChange?: (userId: string, hours: number) => void;
  isUpdating?: boolean;
  onNavigate: (userId: string) => void;
}

const ROLE_ICON: Record<string, React.ReactNode> = {
  owner: <Crown className="h-3 w-3" aria-hidden="true" />,
  admin: <ShieldAlert className="h-3 w-3" aria-hidden="true" />,
};

export function MemberCard({
  member,
  currentUserRole,
  isCurrentUser,
  isLastAdmin = false,
  onRoleChange,
  onRemove,
  onTransferOwnership,
  onAvailabilityChange: _onAvailabilityChange,
  isUpdating = false,
  onNavigate,
}: MemberCardProps) {
  const isAdmin = currentUserRole === 'admin' || currentUserRole === 'owner';
  const isOwner = currentUserRole === 'owner';
  const isMemberOwner = member.role === 'owner';
  const canEditRole = isAdmin && !isMemberOwner && !isCurrentUser;
  const canRemove = isAdmin && !isMemberOwner && !isCurrentUser;
  const removeDisabled = isLastAdmin;
  const canTransferOwnership = isOwner && !isCurrentUser && !isMemberOwner;
  const showActions = canEditRole || canRemove || canTransferOwnership;

  const initials = getInitials(member.fullName, member.email);
  const displayName = member.fullName || member.email.split('@')[0] || member.email;
  const hours = member.weeklyAvailableHours ?? 40;
  const joinedStr = formatJoinDate(member.joinedAt);

  return (
    <Card
      className={cn(
        'relative cursor-pointer px-4 py-4 transition-all duration-200',
        'hover:-translate-y-0.5 hover:shadow-md',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        isCurrentUser && 'ring-1 ring-primary/20'
      )}
      role="article"
      aria-label={`Member card for ${displayName}`}
      tabIndex={0}
      data-testid={`member-card-${member.userId}`}
      onClick={() => onNavigate(member.userId)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onNavigate(member.userId);
        }
      }}
    >
      {/* Top row: role badge + actions */}
      <div className="flex items-start justify-between mb-3">
        <div className="inline-flex items-center gap-1">
          {!member.custom_role && ROLE_ICON[member.role]}
          <MemberRoleBadge role={member.role} customRole={member.custom_role ?? null} />
        </div>

        {showActions && (
          <div onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  aria-label={`Actions for ${displayName}`}
                  disabled={isUpdating}
                >
                  {isUpdating ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <MoreHorizontal className="h-4 w-4" />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canEditRole && (
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <Shield className="mr-2 h-4 w-4" />
                      Change Role
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuItem onClick={() => onRoleChange(member.userId, 'admin')}>
                        <ShieldAlert className="mr-2 h-3.5 w-3.5" />
                        Admin
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onRoleChange(member.userId, 'member')}>
                        <Shield className="mr-2 h-3.5 w-3.5" />
                        Member
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onRoleChange(member.userId, 'guest')}>
                        Guest
                      </DropdownMenuItem>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                )}
                {canTransferOwnership && onTransferOwnership && (
                  <DropdownMenuItem onClick={() => onTransferOwnership(member.userId)}>
                    <Crown className="mr-2 h-4 w-4" />
                    Transfer Ownership
                  </DropdownMenuItem>
                )}
                {(canEditRole || canTransferOwnership) && canRemove && <DropdownMenuSeparator />}
                {canRemove && (
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    disabled={removeDisabled}
                    onClick={() => {
                      if (!removeDisabled) onRemove(member.userId);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove Member
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* Avatar centered */}
      <div className="flex flex-col items-center gap-2">
        <Avatar className="h-12 w-12">
          {member.avatarUrl && (
            <AvatarImage src={member.avatarUrl} alt={`${displayName}'s avatar`} />
          )}
          <AvatarFallback className="text-sm">{initials}</AvatarFallback>
        </Avatar>

        {/* Name */}
        <p className="text-center text-sm font-medium text-foreground truncate max-w-full">
          {displayName}
          {isCurrentUser && <span className="ml-1 text-muted-foreground font-normal">(you)</span>}
        </p>

        {/* Email */}
        <p className="text-center text-xs text-muted-foreground truncate max-w-full">
          {member.email}
        </p>

        {/* Meta row */}
        <p className="text-center text-xs text-muted-foreground mt-1" data-testid="member-meta">
          {hours}h/wk&nbsp;&middot;&nbsp;Joined {joinedStr}
        </p>
      </div>
    </Card>
  );
}
