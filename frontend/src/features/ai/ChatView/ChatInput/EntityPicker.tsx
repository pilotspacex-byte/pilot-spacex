import { memo, useCallback } from 'react';
import type { RefObject } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { FileText, CircleDot, FolderOpen } from 'lucide-react';
import { useEntitySearch } from '../hooks/useEntitySearch';
import type { RecentEntity } from '../hooks/useRecentEntities';

const MAX_ITEMS_PER_GROUP = 5;

const ENTITY_ICONS = {
  Note: FileText,
  Issue: CircleDot,
  Project: FolderOpen,
} as const;

interface EntityPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  query: string;
  workspaceId: string;
  recentEntities: RecentEntity[];
  onSelect: (entity: RecentEntity) => void;
  width?: number;
  /** Ref forwarded to the cmdk Command root DOM node for keyboard event forwarding */
  commandRef?: RefObject<HTMLDivElement | null>;
}

export const EntityPicker = memo<EntityPickerProps>(
  ({ open, onOpenChange: _onOpenChange, query, workspaceId, recentEntities, onSelect, width, commandRef }) => {
    const { notes, issues, projects, isLoading } = useEntitySearch({
      query,
      workspaceId,
    });

    void isLoading;

    const handleNoteSelect = useCallback(
      (noteId: string) => {
        const note = notes.find((n) => n.id === noteId);
        if (note) {
          onSelect({ id: note.id, type: 'Note', title: note.title });
        }
      },
      [notes, onSelect]
    );

    const handleIssueSelect = useCallback(
      (issueId: string) => {
        const issue = issues.find((i) => i.id === issueId);
        if (issue) {
          onSelect({ id: issue.id, type: 'Issue', title: issue.name });
        }
      },
      [issues, onSelect]
    );

    const handleProjectSelect = useCallback(
      (projectId: string) => {
        const project = projects.find((p) => p.id === projectId);
        if (project) {
          onSelect({ id: project.id, type: 'Project', title: project.name });
        }
      },
      [projects, onSelect]
    );

    const handleRecentSelect = useCallback(
      (entityId: string) => {
        const entity = recentEntities.find((e) => e.id === entityId);
        if (entity) {
          onSelect(entity);
        }
      },
      [recentEntities, onSelect]
    );

    const showRecent = !query && recentEntities.length > 0;
    const hasSearchResults = notes.length > 0 || issues.length > 0 || projects.length > 0;

    if (!open) return null;

    return (
      <div
        className={cn('absolute bottom-full left-0 mb-2 z-50')}
        style={width ? { width } : undefined}
        aria-label="Entity picker"
        // Prevent clicks inside the picker from closing it via outside-click handlers
        onMouseDown={(e) => e.preventDefault()}
      >
        <div className="rounded-md border bg-popover text-popover-foreground shadow-md">
          <Command ref={commandRef} filter={() => 1}>
            <CommandList className="max-h-[360px] overflow-y-auto">
              {!query && (
                <div className="px-3 py-1.5 text-xs text-muted-foreground/70 border-b">
                  Type to search across all notes, projects, and issues
                </div>
              )}

              <CommandEmpty>
                {query ? `No results for "${query}"` : 'No results found.'}
              </CommandEmpty>

              {/* Zone 1: Recent entities (hidden when query is non-empty) */}
              {showRecent && (
                <CommandGroup heading="Recent">
                  {recentEntities.slice(0, MAX_ITEMS_PER_GROUP).map((entity) => {
                    const Icon = ENTITY_ICONS[entity.type];
                    return (
                      <CommandItem
                        key={`recent-${entity.id}`}
                        value={`recent-${entity.id}`}
                        onSelect={() => handleRecentSelect(entity.id)}
                        className="flex items-center gap-2 py-1.5 px-2"
                      >
                        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span className="text-sm truncate">{entity.title}</span>
                        <span className="ml-auto text-[10px] text-muted-foreground/60">{entity.type}</span>
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              )}

              {showRecent && hasSearchResults && <CommandSeparator className="my-0.5" />}

              {/* Zone 2: Notes */}
              {notes.length > 0 && (
                <CommandGroup heading="Notes">
                  {notes.slice(0, MAX_ITEMS_PER_GROUP).map((note) => (
                    <CommandItem
                      key={`note-${note.id}`}
                      value={`note-${note.id}`}
                      onSelect={() => handleNoteSelect(note.id)}
                      className="flex items-center gap-2 py-1.5 px-2"
                    >
                      <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="text-sm truncate">{note.title}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}

              {/* Zone 2: Projects */}
              {projects.length > 0 && (
                <CommandGroup heading="Projects">
                  {projects.slice(0, MAX_ITEMS_PER_GROUP).map((project) => (
                    <CommandItem
                      key={`project-${project.id}`}
                      value={`project-${project.id}`}
                      onSelect={() => handleProjectSelect(project.id)}
                      className="flex items-center gap-2 py-1.5 px-2"
                    >
                      <FolderOpen className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="text-sm truncate">{project.name}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}

              {/* Zone 2: Issues */}
              {issues.length > 0 && (
                <CommandGroup heading="Issues">
                  {issues.slice(0, MAX_ITEMS_PER_GROUP).map((issue) => (
                    <CommandItem
                      key={`issue-${issue.id}`}
                      value={`issue-${issue.id}`}
                      onSelect={() => handleIssueSelect(issue.id)}
                      className="flex items-center gap-2 py-1.5 px-2"
                    >
                      <CircleDot className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="text-sm truncate">{issue.name}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </div>
      </div>
    );
  }
);

EntityPicker.displayName = 'EntityPicker';
