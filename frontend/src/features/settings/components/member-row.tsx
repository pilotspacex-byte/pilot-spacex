/**
 * MemberRow - Individual member display within members settings.
 *
 * T023: Avatar, name, email, role badge/selector, remove, transfer ownership.
 */

'use client';

import { Loader2, MoreHorizontal, Shield, ShieldAlert, Trash2, Crown } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
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

interface MemberRowProps {
  member: WorkspaceMember;
  currentUserRole: WorkspaceRole | null;
  isCurrentUser: boolean;
  onRoleChange: (userId: string, role: WorkspaceRole) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
  isUpdating?: boolean;
}

const ROLE_HIERARCHY: Record<string, number> = {
  owner: 0,
  admin: 1,
  member: 2,
  guest: 3,
};

const ROLE_BADGE_VARIANT: Record<string, 'default' | 'secondary' | 'outline'> = {
  owner: 'default',
  admin: 'secondary',
  member: 'outline',
  guest: 'outline',
};

function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name
      .trim()
      .split(/\s+/)
      .filter((p) => p.length > 0);
    if (parts.length >= 2) {
      return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

function formatJoinDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function MemberRow({
  member,
  currentUserRole,
  isCurrentUser,
  onRoleChange,
  onRemove,
  onTransferOwnership,
  isUpdating = false,
}: MemberRowProps) {
  const isAdmin = currentUserRole === 'admin' || currentUserRole === 'owner';
  const isOwner = currentUserRole === 'owner';
  const isMemberOwner = member.role === 'owner';
  const canEditRole = isAdmin && !isMemberOwner && !isCurrentUser;
  const canRemove = isAdmin && !isMemberOwner && !isCurrentUser;
  const canTransferOwnership = isOwner && !isCurrentUser && !isMemberOwner;

  const initials = getInitials(member.full_name, member.email);
  const displayName = member.full_name || member.email.split('@')[0] || member.email;

  return (
    <div
      className="flex flex-col gap-3 rounded-lg border border-border p-4 transition-colors hover:bg-muted/30 sm:flex-row sm:items-center sm:gap-4"
      role="listitem"
    >
      {/* Avatar + Name group */}
      <div className="flex items-center gap-4 min-w-0 flex-1">
        <Avatar className="h-10 w-10 shrink-0">
          {member.avatar_url && (
            <AvatarImage src={member.avatar_url} alt={`${displayName}'s avatar`} />
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
        {formatJoinDate(member.joined_at)}
      </p>

      {/* Role + Actions group */}
      <div className="flex items-center gap-2 sm:gap-4">
        <div className="shrink-0">
          {canEditRole ? (
            <Select
              value={member.role}
              onValueChange={(value) => onRoleChange(member.user_id, value as WorkspaceRole)}
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
            <Badge variant={ROLE_BADGE_VARIANT[member.role] ?? 'outline'} className="capitalize">
              {isMemberOwner && <Crown className="h-3 w-3" />}
              {member.role}
            </Badge>
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
                  <DropdownMenuItem onClick={() => onTransferOwnership(member.user_id)}>
                    <Crown className="mr-2 h-4 w-4" />
                    Transfer Ownership
                  </DropdownMenuItem>
                )}
                {canRemove && (
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onRemove(member.user_id)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove Member
                  </DropdownMenuItem>
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
