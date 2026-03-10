/**
 * MemberRow - Individual member display within members settings.
 *
 * T023: Avatar, name, email, role badge/selector, remove, transfer ownership.
 */

'use client';

import { Loader2, MoreHorizontal, Shield, ShieldAlert, Trash2, Crown } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { WorkspaceMember } from '@/features/issues/hooks/use-workspace-members';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import { ROLE_HIERARCHY, getInitials, formatJoinDate } from '@/features/members/utils/member-utils';
import { MemberRoleBadge } from '@/features/members/components/member-role-badge';

interface MemberRowProps {
  member: WorkspaceMember;
  currentUserRole: WorkspaceRole | null;
  isCurrentUser: boolean;
  isLastAdmin?: boolean;
  onRoleChange: (userId: string, role: WorkspaceRole) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
  onAvailabilityChange?: (userId: string, hours: number) => void;
  isUpdating?: boolean;
  onClick?: () => void;
}

export function MemberRow({
  member,
  currentUserRole,
  isCurrentUser,
  isLastAdmin = false,
  onRoleChange,
  onRemove,
  onTransferOwnership,
  onAvailabilityChange,
  isUpdating = false,
  onClick,
}: MemberRowProps) {
  const isAdmin = currentUserRole === 'admin' || currentUserRole === 'owner';
  const isOwner = currentUserRole === 'owner';
  const isMemberOwner = member.role === 'owner';
  const canEditRole = isAdmin && !isMemberOwner && !isCurrentUser;
  const canRemove = isAdmin && !isMemberOwner && !isCurrentUser;
  const removeDisabled = isLastAdmin;
  const canTransferOwnership = isOwner && !isCurrentUser && !isMemberOwner;
  const canEditAvailability = isCurrentUser || isAdmin;

  const initials = getInitials(member.fullName, member.email);
  const displayName = member.fullName || member.email.split('@')[0] || member.email;

  return (
    <div
      className={`flex flex-col gap-3 rounded-lg border border-border p-4 transition-colors sm:flex-row sm:items-center sm:gap-4 ${onClick ? 'cursor-pointer hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring' : 'hover:bg-muted/30'}`}
      role={onClick ? 'button' : 'listitem'}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      aria-label={onClick ? `View profile for ${member.fullName ?? member.email}` : undefined}
      aria-haspopup={onClick ? 'dialog' : undefined}
    >
      {/* Avatar + Name group */}
      <div className="flex items-center gap-4 min-w-0 flex-1">
        <Avatar className="h-10 w-10 shrink-0">
          {member.avatarUrl && (
            <AvatarImage src={member.avatarUrl} alt={`${displayName}'s avatar`} />
          )}
          <AvatarFallback className="text-sm">{initials}</AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate font-medium text-foreground">
              {displayName}
              {isCurrentUser && <span className="ml-1.5 text-sm text-muted-foreground">(you)</span>}
            </p>
          </div>
          <p className="truncate text-sm text-muted-foreground">{member.email}</p>
        </div>
      </div>

      {/* Joined Date */}
      <p className="hidden text-sm text-muted-foreground sm:block">
        {formatJoinDate(member.joinedAt)}
      </p>

      {/* Weekly Available Hours (T-246) */}
      <div className="hidden items-center gap-1 sm:flex" onClick={(e) => e.stopPropagation()}>
        <input
          type="number"
          min={0}
          max={168}
          step={1}
          defaultValue={member.weeklyAvailableHours ?? 40}
          disabled={!canEditAvailability || isUpdating}
          aria-label={`Weekly available hours for ${member.fullName ?? member.email}`}
          onBlur={(e) => {
            if (!onAvailabilityChange) return;
            const val = parseFloat(e.target.value);
            if (!isNaN(val) && val >= 0 && val <= 168) {
              onAvailabilityChange(member.userId, val);
            }
          }}
          className="h-7 w-16 rounded-md border border-input bg-background px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        />
        <span className="text-xs text-muted-foreground">h/wk</span>
      </div>

      {/* Role + Actions group */}
      <div className="flex items-center gap-2 sm:gap-4" onClick={(e) => e.stopPropagation()}>
        <div className="shrink-0">
          {canEditRole ? (
            <Select
              value={member.role}
              onValueChange={(value) => onRoleChange(member.userId, value as WorkspaceRole)}
              disabled={isUpdating}
            >
              <SelectTrigger
                className="w-full sm:w-[110px]"
                aria-label={`Change role for ${displayName}`}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">
                  <div className="flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    Admin
                  </div>
                </SelectItem>
                <SelectItem value="member">
                  <div className="flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5" />
                    Member
                  </div>
                </SelectItem>
                <SelectItem value="guest">Guest</SelectItem>
              </SelectContent>
            </Select>
          ) : (
            <div className="inline-flex items-center gap-1">
              {isMemberOwner && <Crown className="h-3 w-3" />}
              <MemberRoleBadge role={member.role} customRole={member.custom_role ?? null} />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="shrink-0">
          {(canRemove || canTransferOwnership) && (
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
                {canTransferOwnership && onTransferOwnership && (
                  <DropdownMenuItem onClick={() => onTransferOwnership(member.userId)}>
                    <Crown className="mr-2 h-4 w-4" />
                    Transfer Ownership
                  </DropdownMenuItem>
                )}
                {canRemove && (
                  <span title={removeDisabled ? 'Cannot remove the only admin' : undefined}>
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
                  </span>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </div>
  );
}

export { ROLE_HIERARCHY };
