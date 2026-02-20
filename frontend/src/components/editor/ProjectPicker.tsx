'use client';

/**
 * ProjectPicker - Searchable combobox for changing a note's project assignment.
 * Uses shadcn/ui Popover + Command (cmdk) with optimistic TanStack Query mutation.
 *
 * @see tmp/note-editor-ui-design.md Section 5 for design spec
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderKanban, ChevronDown, Check, X } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { projectsApi } from '@/services/api/projects';
import { notesApi } from '@/services/api/notes';
import type { Project } from '@/types';

export interface ProjectPickerProps {
  /** Current workspace ID for fetching projects and updating note */
  workspaceId: string;
  /** Note ID to update when project changes */
  noteId: string;
  /** Currently assigned project ID */
  currentProjectId?: string;
  /** Callback when project changes (for optimistic UI in parent) */
  onProjectChange?: (projectId: string | null) => void;
}

export function ProjectPicker({
  workspaceId,
  noteId,
  currentProjectId,
  onProjectChange,
}: ProjectPickerProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: projects } = useQuery({
    queryKey: ['projects', workspaceId],
    queryFn: () => projectsApi.list(workspaceId),
    staleTime: 5 * 60 * 1000,
    enabled: !!workspaceId,
  });

  const currentProject = projects?.items?.find((p: Project) => p.id === currentProjectId);

  const mutation = useMutation({
    mutationFn: (projectId: string | null) =>
      notesApi.update(workspaceId, noteId, { projectId: projectId ?? undefined }),
    onMutate: async (projectId) => {
      // Cancel outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: ['notes', noteId] });
      // Snapshot previous data for rollback on error
      const previousNote = queryClient.getQueryData(['notes', noteId]);
      onProjectChange?.(projectId);
      return { previousNote };
    },
    onError: (_err, _projectId, context) => {
      // Restore previous data if mutation fails
      if (context?.previousNote !== undefined) {
        queryClient.setQueryData(['notes', noteId], context.previousNote);
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      void queryClient.invalidateQueries({ queryKey: ['notes', noteId] });
    },
  });

  const handleSelect = (projectId: string | null) => {
    if (projectId === currentProjectId) {
      setOpen(false);
      return;
    }
    mutation.mutate(projectId);
    setOpen(false);
  };

  const projectList = projects?.items ?? [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-controls="project-picker-list"
          aria-label={currentProject ? `Project: ${currentProject.name}` : 'Add project'}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-sm px-2 py-1',
            'text-xs font-medium text-muted-foreground',
            'border border-transparent transition-colors',
            'hover:bg-background-subtle hover:border-border-subtle',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
            'h-6 cursor-pointer group'
          )}
          data-testid="project-picker-trigger"
        >
          <FolderKanban className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {currentProject ? (
            <span className="truncate max-w-[140px]">{currentProject.name}</span>
          ) : (
            <span className="italic opacity-60">Add project...</span>
          )}
          <ChevronDown
            className="h-2.5 w-2.5 opacity-0 group-hover:opacity-100 transition-opacity"
            aria-hidden="true"
          />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[260px] p-0" align="start" sideOffset={4}>
        <Command>
          <CommandInput placeholder="Search projects..." className="h-8 text-xs" />
          <CommandList id="project-picker-list" className="max-h-[240px]">
            <CommandEmpty>No projects found.</CommandEmpty>
            <CommandGroup>
              {projectList.map((project: Project) => {
                const done = project.completedIssueCount;
                return (
                  <CommandItem
                    key={project.id}
                    value={project.name}
                    onSelect={() => handleSelect(project.id)}
                    className="flex items-center gap-2 text-xs"
                    data-testid={`project-picker-item-${project.id}`}
                  >
                    <span
                      className="h-2 w-2 rounded-full flex-shrink-0 bg-primary"
                      aria-hidden="true"
                    />
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="truncate font-medium">{project.name}</span>
                      <span className="text-[10px] text-muted-foreground">
                        {done} of {project.issueCount} issues done
                      </span>
                    </div>
                    {project.id === currentProjectId && (
                      <Check className="h-3 w-3 text-primary flex-shrink-0" aria-hidden="true" />
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {currentProjectId && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => handleSelect(null)}
                    className="text-xs text-muted-foreground"
                    data-testid="project-picker-remove"
                  >
                    <X className="h-3 w-3" aria-hidden="true" />
                    <span>Remove project</span>
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
