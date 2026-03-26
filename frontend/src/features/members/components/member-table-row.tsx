/**
 * MemberTableRow — Table-row variant of MemberCard for the Members table layout.
 *
 * E-04: Renders a workspace member as a <TableRow> inside a shadcn Table.
 * Keeps the same prop API and actions as MemberCard.
 */

'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TableCell, TableRow } from '@/components/ui/table';
import type { WorkspaceMember } from '@/features/issues/hooks/use-workspace-members';
import { formatJoinDate, getInitials } from '@/features/members/utils/member-utils';
import type { WorkspaceRole } from '@/stores/WorkspaceStore';
import {
  Crown,
  FolderKanban,
  Loader2,
  MoreHorizontal,
  Trash2,
} from 'lucide-react';
import { MemberRoleBadge } from './member-role-badge';
import { ProjectChips } from './project-chips';

interface MemberTableRowProps {
  member: WorkspaceMember;
  currentUserRole: WorkspaceRole | null;
  isCurrentUser: boolean;
  isLastAdmin?: boolean;
  onRoleChange: (userId: string, role: WorkspaceRole) => void;
  onRemove: (userId: string) => void;
  onTransferOwnership?: (userId: string) => void;
  onEditAssignments?: (userId: string) => void;
  isUpdating?: boolean;
  onNavigate: (userId: string) => void;
}

export function MemberTableRow({
  member,
  currentUserRole,
  isCurrentUser,
  isLastAdmin = false,
  onRemove,
  onTransferOwnership,
  isUpdating = false,
  onEditAssignments,
  onNavigate,
}: MemberTableRowProps) {
  const isAdmin = currentUserRole === 'admin' || currentUserRole === 'owner';
  const isOwner = currentUserRole === 'owner';
  const isMemberOwner = member.role === 'owner';
  const isMemberAdmin = member.role === 'admin';
  // Admins cannot remove members with equal or higher role (admin/owner); only owners can remove admins
  const canRemove =
    isAdmin && !isMemberOwner && !isCurrentUser && (isOwner || !isMemberAdmin);
  const removeDisabled = isLastAdmin;
  const canTransferOwnership = isOwner && !isCurrentUser && !isMemberOwner;
  const canEditAssignments = isAdmin && !isCurrentUser && !!onEditAssignments;
  const showActions = canRemove || canTransferOwnership || canEditAssignments;

  const initials = getInitials(member.fullName, member.email);
  const displayName = member.fullName || member.email.split('@')[0] || member.email;
  const joinedStr = formatJoinDate(member.joinedAt);

  return (
    <TableRow
      className="cursor-pointer hover:bg-accent/50"
      data-testid={`member-row-${member.userId}`}
      onClick={() => onNavigate(member.userId)}
    >
      {/* Avatar + Name */}
      <TableCell>
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8 shrink-0">
            {member.avatarUrl && (
              <AvatarImage src={member.avatarUrl} alt={`${displayName}'s avatar`} />
            )}
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="truncate text-sm font-medium">{displayName}</span>
              {isCurrentUser && (
                <span className="shrink-0 rounded-full bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
                  you
                </span>
              )}
            </div>
          </div>
        </div>
      </TableCell>

      {/* Email */}
      <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
        {member.email}
      </TableCell>

      {/* Role */}
      <TableCell>
        <MemberRoleBadge role={member.role} customRole={member.custom_role ?? null} />
      </TableCell>

      {/* Projects */}
      <TableCell
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
        className="hidden md:table-cell"
      >
        {member.projects && member.projects.length > 0 ? (
          <ProjectChips projects={member.projects} maxVisible={3} />
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>

      {/* Joined */}
      <TableCell className="hidden sm:table-cell text-xs text-muted-foreground whitespace-nowrap">
        {joinedStr}
      </TableCell>

      {/* Actions */}
      <TableCell
        className="w-10 text-right"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {showActions && (
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
              {canEditAssignments && (
                <DropdownMenuItem onClick={() => onEditAssignments!(member.userId)}>
                  <FolderKanban className="mr-2 h-4 w-4" />
                  Edit Permissions
                </DropdownMenuItem>
              )}
              {canTransferOwnership && onTransferOwnership && (
                <DropdownMenuItem onClick={() => onTransferOwnership(member.userId)}>
                  <Crown className="mr-2 h-4 w-4" />
                  Transfer Ownership
                </DropdownMenuItem>
              )}
              {canTransferOwnership && canRemove && <DropdownMenuSeparator />}
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
        )}
      </TableCell>
    </TableRow>
  );
}
