/**
 * ProjectMembersTab — Member list for a project (US1, FR-01).
 *
 * Uses the workspace members API filtered by project_id.
 * Supports server-side search with 300ms debounce and pagination.
 * Admin-only action: remove member from project.
 */

'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useWorkspaceMembers } from '@/features/issues/hooks/use-workspace-members';
import { getInitials } from '@/features/members/utils/member-utils';
import { useRemoveProjectMember } from '@/services/api/project-members';
import { ChevronLeft, ChevronRight, Loader2, Search, UserMinus } from 'lucide-react';
import * as React from 'react';
import { toast } from 'sonner';

const PAGE_SIZE = 25;

interface ProjectMembersTabProps {
  workspaceId: string;
  projectId: string;
  isAdmin: boolean;
}

function PaginationControls({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 pt-2">
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <span className="text-xs text-muted-foreground">
        {page} / {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

export function ProjectMembersTab({ workspaceId, projectId, isAdmin }: ProjectMembersTabProps) {
  const [search, setSearch] = React.useState('');
  const [debouncedSearch, setDebouncedSearch] = React.useState('');
  const [page, setPage] = React.useState(1);

  // Debounce search by 300ms
  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Reset page when search changes
  React.useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const { data: membersData, isLoading } = useWorkspaceMembers(workspaceId, {
    projectId,
    search: debouncedSearch,
    page,
    pageSize: PAGE_SIZE,
  });

  const removeMember = useRemoveProjectMember(workspaceId, projectId);

  const members = membersData?.items ?? [];
  const totalPages = Math.max(1, Math.ceil((membersData?.total ?? 0) / PAGE_SIZE));

  function handleRemove(userId: string) {
    removeMember.mutate(userId, {
      onSuccess: () => toast.success('Member removed from project'),
      onError: () => toast.error('Failed to remove member'),
    });
  }

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-3xl space-y-4">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search members…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <div className="text-sm text-muted-foreground">
        {membersData?.total ?? 0} {(membersData?.total ?? 0) === 1 ? 'member' : 'members'}
      </div>

      {members.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {debouncedSearch
            ? 'No members match your search.'
            : 'No members assigned to this project yet.'}
        </p>
      ) : (
        <>
          <ul className="space-y-2">
            {members.map((member) => {
              const initials = getInitials(member.fullName, member.email);
              const displayName = member.fullName ?? member.email.split('@')[0];
              return (
                <li
                  key={member.userId}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-3"
                >
                  <Avatar className="h-9 w-9 flex-shrink-0">
                    <AvatarImage src={member.avatarUrl ?? undefined} />
                    <AvatarFallback className="text-xs">{initials}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{displayName}</p>
                    <p className="text-xs text-muted-foreground truncate">{member.email}</p>
                  </div>
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive flex-shrink-0"
                      title="Remove from project"
                      onClick={() => handleRemove(member.userId)}
                      disabled={removeMember.isPending}
                    >
                      {removeMember.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <UserMinus className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
          <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
