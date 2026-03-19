/**
 * MemberCard - Row component for displaying a workspace member in a list.
 *
 * Horizontal layout: avatar, name/email, role badge, meta, actions.
 * Admin-only actions dropdown with role change sub-menu.
 */

'use client';

import { Crown, Loader2, MoreHorizontal, Shield, ShieldAlert, Trash2 } from 'lucide-react';
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
    <div
      className={cn(
        'group flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3 transition-all duration-200',
        'hover:bg-accent/50 hover:shadow-warm-sm',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'cursor-pointer',
        isCurrentUser && 'ring-1 ring-primary/20 bg-primary/[0.02]'
      )}
      role="article"
      aria-label={`Member: ${displayName}`}
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
      {/* Avatar */}
      <Avatar className="h-10 w-10 shrink-0">
        {member.avatarUrl && <AvatarImage src={member.avatarUrl} alt={`${displayName}'s avatar`} />}
        <AvatarFallback className="text-xs">{initials}</AvatarFallback>
      </Avatar>

      {/* Name & email */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium text-foreground">{displayName}</p>
          {isCurrentUser && (
            <span className="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
              you
            </span>
          )}
        </div>
        {member.fullName && (
          <p className="truncate text-xs text-muted-foreground">{member.email}</p>
        )}
      </div>

      {/* Role badge */}
      <div className="hidden shrink-0 items-center gap-1 sm:flex">
        {!member.custom_role && ROLE_ICON[member.role]}
        <MemberRoleBadge role={member.role} customRole={member.custom_role ?? null} />
      </div>

      {/* Meta: availability & joined */}
      <div className="hidden shrink-0 text-right md:block" data-testid="member-meta">
        <p className="text-xs text-muted-foreground">{hours}h/wk</p>
        <p className="text-[11px] text-muted-foreground/70">Joined {joinedStr}</p>
      </div>

      {/* Actions */}
      {showActions && (
        <div
          className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
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
  );
}
