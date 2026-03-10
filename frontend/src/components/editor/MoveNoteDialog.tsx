'use client';

/**
 * MoveNoteDialog - Project picker dialog for assigning a note to a project.
 *
 * Used by two flows:
 * 1. "New Note" project selection step (after TemplatePicker in sidebar.tsx)
 * 2. "Move..." option in the InlineNoteHeader options dropdown
 *
 * @module components/editor/MoveNoteDialog
 */
import { useState, useMemo } from 'react';
import { Folder, X, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { useProjects, selectAllProjects } from '@/features/projects/hooks/useProjects';

export interface MoveNoteDialogProps {
  workspaceId: string;
  /** Pre-selects this project in the picker. null = "No project (root)". */
  currentProjectId?: string | null;
  /** Label for the confirm button. Defaults to "Confirm". */
  confirmLabel?: string;
  onSelect: (projectId: string | null) => void;
  onClose: () => void;
}

export function MoveNoteDialog({
  workspaceId,
  currentProjectId = null,
  confirmLabel = 'Confirm',
  onSelect,
  onClose,
}: MoveNoteDialogProps) {
  const [selected, setSelected] = useState<string | null>(currentProjectId ?? null);
  const [search, setSearch] = useState('');

  const { data: projectsData, isLoading } = useProjects({ workspaceId });
  const projects = useMemo(() => selectAllProjects(projectsData), [projectsData]);

  const filteredProjects = useMemo(() => {
    if (!search.trim()) return projects;
    const q = search.toLowerCase();
    return projects.filter((p) => p.name.toLowerCase().includes(q));
  }, [projects, search]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Choose a project"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative flex max-h-[70vh] w-full max-w-[400px] flex-col overflow-hidden rounded-xl bg-background shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <h2 className="text-sm font-semibold text-foreground">Add to project</h2>
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close"
            onClick={onClose}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-border px-3 py-2">
          <Search className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Input
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects…"
            className="h-6 border-none bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
          />
        </div>

        {/* Project list */}
        <div className="overflow-y-auto px-3 py-2">
          {/* No project (root) option */}
          <button
            type="button"
            onClick={() => setSelected(null)}
            className={cn(
              'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
              selected === null
                ? 'bg-primary/5 text-foreground'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            )}
          >
            <Folder className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span className="flex-1 text-left">No project (root)</span>
            {selected === null && (
              <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
            )}
          </button>

          {/* Loading state */}
          {isLoading && (
            <div className="mt-1 space-y-1 px-1">
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-3/4 rounded-lg" />
            </div>
          )}

          {/* Project rows */}
          {!isLoading &&
            filteredProjects.map((project) => (
              <button
                key={project.id}
                type="button"
                onClick={() => setSelected(project.id)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
                  selected === project.id
                    ? 'bg-primary/5 text-foreground'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                )}
              >
                {project.icon ? (
                  <span className="text-base leading-none shrink-0" aria-hidden="true">
                    {project.icon}
                  </span>
                ) : (
                  <Folder className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                )}
                <span className="flex-1 truncate text-left">{project.name}</span>
                {selected === project.id && (
                  <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
                )}
              </button>
            ))}

          {!isLoading && filteredProjects.length === 0 && search && (
            <p className="px-3 py-2 text-xs text-muted-foreground">No projects found</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => onSelect(selected)}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
