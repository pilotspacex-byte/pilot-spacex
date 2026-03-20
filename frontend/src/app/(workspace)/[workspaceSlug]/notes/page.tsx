'use client';

/**
 * Notes List Page - T113
 * Grid/List view, search, filter, sort, infinite scroll
 */
import { useCallback, useMemo, useRef, useState, use } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'motion/react';
import {
  FileText,
  FolderKanban,
  Plus,
  Search,
  Grid3X3,
  List,
  SortAsc,
  SortDesc,
  Filter,
  Pin,
  Calendar,
  Clock,
  Loader2,
  X,
  Check,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '@/components/ui/command';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useVirtualizer } from '@tanstack/react-virtual';
import { cn } from '@/lib/utils';
import { useInfiniteNotes, notesKeys } from '@/features/notes/hooks';
import { useCreateNote, createNoteDefaults } from '@/features/notes/hooks';
import { NoteGridCard, NoteListRow, GridSkeleton, EmptyState } from './note-card-components';
import { useWorkspaceStore } from '@/stores/RootStore';
import { projectsApi } from '@/services/api/projects';
import { notesApi } from '@/services/api';
import type { Project } from '@/types';

type ViewMode = 'grid' | 'list';
type SortBy = 'updated' | 'created' | 'title' | 'wordCount';
type SortOrder = 'asc' | 'desc';

interface NotesPageProps {
  params: Promise<{ workspaceSlug: string }>;
}

/**
 * Notes List Page Component
 */
const NotesPage = observer(function NotesPage({ params }: NotesPageProps) {
  const { workspaceSlug } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const workspaceStore = useWorkspaceStore();
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';

  // Seed project filter from ?projectId=<id> (e.g. from ProjectNotesPanel "View all" link)
  const initialProjectId = searchParams.get('projectId');

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('updated');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filterPinned, setFilterPinned] = useState<boolean | undefined>(undefined);
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>(
    initialProjectId ? [initialProjectId] : []
  );
  const [pendingProjectIds, setPendingProjectIds] = useState<string[]>(
    initialProjectId ? [initialProjectId] : []
  );
  const [projectFilterOpen, setProjectFilterOpen] = useState(false);

  // Get workspace ID from store or slug
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  // Fetch all projects for lookup on note cards
  const { data: projectsData } = useQuery({
    queryKey: ['projects', 'list', workspaceId],
    queryFn: () => projectsApi.list(workspaceId),
    enabled: !!workspaceId,
    staleTime: 5 * 60 * 1000,
  });

  const projectMap = useMemo(() => {
    const map = new Map<string, Project>();
    for (const project of projectsData?.items ?? []) {
      map.set(project.id, project);
    }
    return map;
  }, [projectsData]);

  // Set for O(1) lookup in CommandItem renders
  const pendingProjectIdSet = useMemo(() => new Set(pendingProjectIds), [pendingProjectIds]);

  // Fetch notes with infinite scroll
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } = useInfiniteNotes({
    workspaceId,
    isPinned: filterPinned,
    projectIds: selectedProjectIds.length > 0 ? selectedProjectIds : undefined,
    pageSize: 20,
    enabled: !!workspaceId,
  });

  // Create note mutation
  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  // Flatten pages into single array
  const allNotes = useMemo(() => {
    return data?.pages.flatMap((page) => page.items) ?? [];
  }, [data]);

  // Filter and sort notes
  const filteredNotes = useMemo(() => {
    let notes = [...allNotes];

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      notes = notes.filter(
        (note) =>
          note.title.toLowerCase().includes(query) ||
          note.topics?.some((t) => t.toLowerCase().includes(query))
      );
    }

    // Sort
    notes.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'updated':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
        case 'created':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'title':
          comparison = a.title.localeCompare(b.title);
          break;
        case 'wordCount':
          comparison = a.wordCount - b.wordCount;
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    // Pinned notes first
    notes.sort((a, b) => (b.isPinned ? 1 : 0) - (a.isPinned ? 1 : 0));

    return notes;
  }, [allNotes, searchQuery, sortBy, sortOrder]);

  // Virtual scroll for list view
  const LIST_ITEM_HEIGHT = 72;
  const INITIAL_ANIMATED_COUNT = 15;
  const listParentRef = useRef<HTMLDivElement>(null);

  const listVirtualizer = useVirtualizer({
    count: filteredNotes.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => LIST_ITEM_HEIGHT,
    overscan: 5,
  });

  // Prefetch note detail on hover for instant navigation
  const handlePrefetchNote = useCallback(
    (noteId: string) => {
      queryClient.prefetchQuery({
        queryKey: notesKeys.detail(workspaceId, noteId),
        queryFn: () => notesApi.get(workspaceId, noteId),
        staleTime: 60_000,
      });
    },
    [queryClient, workspaceId]
  );

  // Handle create note
  const handleCreateNote = useCallback(() => {
    createNote.mutate(createNoteDefaults());
  }, [createNote]);

  // Handle infinite scroll
  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border/60 bg-background-subtle/30 px-4 py-5 sm:px-6 sm:py-7">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
              Notes
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">Your collaborative thinking space</p>
          </div>
          {canCreateContent && (
            <Button
              onClick={handleCreateNote}
              disabled={createNote.isPending}
              className="gap-2 shadow-warm-sm"
              data-testid="create-note-button"
            >
              {createNote.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">New Note</span>
              <span className="sm:hidden">New</span>
            </Button>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col gap-2 border-b border-border px-4 py-2 sm:flex-row sm:items-center sm:gap-4 sm:px-6">
        {/* Search */}
        <div className="relative sm:flex-1 sm:max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes..."
            className="pl-9"
          />
        </div>

        {/* View controls */}
        <div className="flex items-center gap-2">
          {/* Filter (pinned) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Filter
                {filterPinned !== undefined && (
                  <Badge variant="secondary" className="ml-1 text-[10px]">
                    1
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Filter by</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                checked={filterPinned === true}
                onCheckedChange={(checked) => setFilterPinned(checked ? true : undefined)}
              >
                <Pin className="mr-2 h-4 w-4" />
                Pinned only
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Projects filter */}
          <DropdownMenu
            open={projectFilterOpen}
            onOpenChange={(open) => {
              setProjectFilterOpen(open);
              if (open) setPendingProjectIds(selectedProjectIds);
            }}
          >
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <FolderKanban className="h-4 w-4" />
                Projects
                {selectedProjectIds.length > 0 && (
                  <Badge variant="secondary" className="ml-1 text-[10px]">
                    {selectedProjectIds.length}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64 p-0">
              <Command>
                <CommandInput placeholder="Search projects..." />
                <CommandEmpty>No projects found</CommandEmpty>
                <CommandGroup className="max-h-48 overflow-y-auto">
                  {(projectsData?.items ?? []).map((project) => {
                    const isSelected = pendingProjectIdSet.has(project.id);
                    return (
                      <CommandItem
                        key={project.id}
                        onSelect={() => {
                          setPendingProjectIds((prev) =>
                            isSelected
                              ? prev.filter((id) => id !== project.id)
                              : [...prev, project.id]
                          );
                        }}
                      >
                        <div
                          className={cn(
                            'mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary',
                            isSelected ? 'bg-primary text-primary-foreground' : 'opacity-50'
                          )}
                        >
                          {isSelected && <Check className="h-3 w-3" />}
                        </div>
                        {project.icon && <span className="mr-2 text-sm">{project.icon}</span>}
                        <FolderKanban
                          className={cn('mr-2 h-4 w-4', project.icon ? 'hidden' : '')}
                        />
                        <span className="truncate">{project.name}</span>
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
                <div className="border-t border-border p-2">
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      setSelectedProjectIds(pendingProjectIds);
                      setProjectFilterOpen(false);
                    }}
                  >
                    Done
                  </Button>
                </div>
              </Command>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Sort */}
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortBy)}>
            <SelectTrigger className="min-w-[140px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Last modified
                </div>
              </SelectItem>
              <SelectItem value="created">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Created
                </div>
              </SelectItem>
              <SelectItem value="title">
                <div className="flex items-center gap-2">
                  <SortAsc className="h-4 w-4" />
                  Alphabetical
                </div>
              </SelectItem>
              <SelectItem value="wordCount">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Word count
                </div>
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Sort order */}
          <Button
            variant="outline"
            size="icon"
            onClick={() => setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'))}
          >
            {sortOrder === 'asc' ? (
              <SortAsc className="h-4 w-4" />
            ) : (
              <SortDesc className="h-4 w-4" />
            )}
          </Button>

          {/* View mode */}
          <div className="flex items-center rounded-md border border-border">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon-sm"
              onClick={() => setViewMode('grid')}
              className="rounded-r-none"
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon-sm"
              onClick={() => setViewMode('list')}
              className="rounded-l-none"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Project filter chips */}
      {selectedProjectIds.length > 0 && (
        <div className="flex flex-wrap gap-2 px-4 py-2 sm:px-6 border-b border-border">
          {selectedProjectIds.map((pid) => {
            const project = projectMap.get(pid);
            return (
              <Badge key={pid} variant="secondary" className="gap-1 pr-1.5">
                <FolderKanban className="h-3 w-3" />
                {project?.name ?? pid}
                <button
                  type="button"
                  className="ml-0.5 rounded-sm hover:bg-muted-foreground/20"
                  onClick={() => setSelectedProjectIds((prev) => prev.filter((id) => id !== pid))}
                  aria-label={`Remove ${project?.name ?? pid} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setSelectedProjectIds([])}
          >
            Clear all
          </button>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex-1 overflow-auto p-4 sm:p-6">
          <GridSkeleton />
        </div>
      ) : filteredNotes.length === 0 ? (
        <div className="flex-1 overflow-auto p-4 sm:p-6">
          <EmptyState onCreate={canCreateContent ? handleCreateNote : undefined} />
        </div>
      ) : viewMode === 'grid' ? (
        <div className="flex-1 overflow-auto p-4 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence mode="popLayout">
              {filteredNotes.map((note, index) => (
                <motion.div
                  key={note.id}
                  initial={index < INITIAL_ANIMATED_COUNT ? { opacity: 0, y: 12 } : false}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={
                    index < INITIAL_ANIMATED_COUNT
                      ? { delay: Math.min(index * 0.03, 0.3) }
                      : undefined
                  }
                >
                  <NoteGridCard
                    note={note}
                    workspaceSlug={workspaceSlug}
                    projectMap={projectMap}
                    onPrefetch={() => handlePrefetchNote(note.id)}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          {/* Load more (grid) */}
          {hasNextPage && (
            <div className="flex justify-center pt-8">
              <Button variant="outline" onClick={handleLoadMore} disabled={isFetchingNextPage}>
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load more'
                )}
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div ref={listParentRef} className="flex-1 overflow-auto p-4 sm:p-6">
          <div
            style={{
              height: listVirtualizer.getTotalSize(),
              width: '100%',
              position: 'relative',
            }}
          >
            {listVirtualizer.getVirtualItems().map((virtualRow) => {
              const note = filteredNotes[virtualRow.index];
              if (!note) return null;
              const isInitialBatch = virtualRow.index < INITIAL_ANIMATED_COUNT;
              return (
                <div
                  key={note.id}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: virtualRow.size,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {isInitialBatch ? (
                    <motion.div
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: Math.min(virtualRow.index * 0.02, 0.2) }}
                    >
                      <NoteListRow
                        note={note}
                        workspaceSlug={workspaceSlug}
                        projectMap={projectMap}
                        onPrefetch={() => handlePrefetchNote(note.id)}
                      />
                    </motion.div>
                  ) : (
                    <NoteListRow
                      note={note}
                      workspaceSlug={workspaceSlug}
                      projectMap={projectMap}
                      onPrefetch={() => handlePrefetchNote(note.id)}
                    />
                  )}
                </div>
              );
            })}
          </div>
          {/* Load more (list) */}
          {hasNextPage && (
            <div className="flex justify-center pt-8">
              <Button variant="outline" onClick={handleLoadMore} disabled={isFetchingNextPage}>
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load more'
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default NotesPage;
