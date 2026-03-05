'use client';

/**
 * Notes List Page - T113
 * Grid/List view, search, filter, sort, infinite scroll
 */
import { useCallback, useMemo, useRef, useState, use } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'motion/react';
import { formatDistanceToNow } from 'date-fns';
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
} from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
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
import { useWorkspaceStore } from '@/stores/RootStore';
import { projectsApi } from '@/services/api/projects';
import { notesApi } from '@/services/api';
import type { Note, Project } from '@/types';

type ViewMode = 'grid' | 'list';
type SortBy = 'updated' | 'created' | 'title' | 'wordCount';
type SortOrder = 'asc' | 'desc';

interface NotesPageProps {
  params: Promise<{ workspaceSlug: string }>;
}

/**
 * Note card component for grid view
 */
function NoteGridCard({
  note,
  workspaceSlug,
  projectMap,
  onPrefetch,
}: {
  note: Note;
  workspaceSlug: string;
  projectMap: Map<string, Project>;
  onPrefetch: () => void;
}) {
  const updatedAt = formatDistanceToNow(new Date(note.updatedAt), { addSuffix: true });
  const topics = note.topics ?? [];
  const linkedIssues = note.linkedIssues ?? [];
  const project = note.projectId ? projectMap.get(note.projectId) : undefined;

  return (
    <Link href={`/${workspaceSlug}/notes/${note.id}`} onMouseEnter={onPrefetch}>
      <Card
        className={cn(
          'group cursor-pointer transition-all duration-200',
          'hover:shadow-warm-md hover:-translate-y-0.5'
        )}
      >
        <CardContent className="p-5">
          <div className="mb-3 flex items-start justify-between">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="flex items-center gap-2">
              {note.isPinned && <Pin className="h-3.5 w-3.5 text-amber-500" />}
            </div>
          </div>
          <h3 className="mb-1 font-medium text-foreground transition-colors group-hover:text-primary line-clamp-1">
            {note.title || 'Untitled'}
          </h3>

          {/* Project reference */}
          {project && (
            <div className="flex items-center gap-1.5 mb-2 text-xs text-muted-foreground">
              <FolderKanban className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{project.name}</span>
              <div className="h-1 w-10 rounded-full bg-border overflow-hidden flex-shrink-0">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{
                    width: `${((project.issueCount - project.openIssueCount) / Math.max(project.issueCount, 1)) * 100}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Linked issues with state colors, or topics fallback */}
          {linkedIssues.length > 0 ? (
            <div className="flex items-center gap-1 mb-3 flex-wrap">
              {linkedIssues.slice(0, 3).map((issue) => (
                <span
                  key={issue.id}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted/50"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: issue.state.color }}
                  />
                  {issue.identifier}
                </span>
              ))}
              {linkedIssues.length > 3 && (
                <span className="text-[10px] text-muted-foreground">
                  +{linkedIssues.length - 3}
                </span>
              )}
            </div>
          ) : (
            <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
              {topics.length > 0 ? topics.join(', ') : 'No topics'}
            </p>
          )}

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{(note.wordCount ?? 0).toLocaleString()} words</span>
            <span>Updated {updatedAt}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

/**
 * Note row component for list view
 */
function NoteListRow({
  note,
  workspaceSlug,
  projectMap,
  onPrefetch,
}: {
  note: Note;
  workspaceSlug: string;
  projectMap: Map<string, Project>;
  onPrefetch: () => void;
}) {
  const updatedAt = formatDistanceToNow(new Date(note.updatedAt), { addSuffix: true });
  const topics = note.topics ?? [];
  const linkedIssues = note.linkedIssues ?? [];
  const project = note.projectId ? projectMap.get(note.projectId) : undefined;

  return (
    <Link href={`/${workspaceSlug}/notes/${note.id}`} onMouseEnter={onPrefetch}>
      <div
        className={cn(
          'group flex items-center gap-4 rounded-lg border border-border p-4',
          'transition-all hover:border-primary/30 hover:bg-accent/50'
        )}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
          <FileText className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-foreground group-hover:text-primary truncate">
              {note.title || 'Untitled'}
            </h3>
            {note.isPinned && <Pin className="h-3.5 w-3.5 text-amber-500 shrink-0" />}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {project && (
              <span className="flex items-center gap-1 truncate">
                <FolderKanban className="h-3 w-3 flex-shrink-0" />
                {project.name}
              </span>
            )}
            {project && topics.length > 0 && <span className="text-border">&middot;</span>}
            <span className="truncate">
              {topics.length > 0 ? topics.join(', ') : !project ? 'No topics' : ''}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground shrink-0">
          <span>{(note.wordCount ?? 0).toLocaleString()} words</span>
          {linkedIssues.length > 0 && (
            <div className="flex items-center gap-1">
              {linkedIssues.slice(0, 3).map((issue) => (
                <span
                  key={issue.id}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted/50"
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: issue.state.color }}
                  />
                  {issue.identifier}
                </span>
              ))}
              {linkedIssues.length > 3 && (
                <span className="text-[10px] text-muted-foreground">
                  +{linkedIssues.length - 3}
                </span>
              )}
            </div>
          )}
          <span className="w-24 text-right">{updatedAt}</span>
        </div>
      </div>
    </Link>
  );
}

/**
 * Loading skeleton for grid view
 */
function GridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-5">
            <div className="mb-3 flex items-start justify-between">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-5 w-3/4 mb-2" />
            <Skeleton className="h-4 w-full mb-1" />
            <Skeleton className="h-4 w-2/3 mb-3" />
            <div className="flex justify-between">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-24" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Empty state component
 */
function EmptyState({ onCreate }: { onCreate?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-4">
        <FileText className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1">No notes yet</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        Start capturing your thoughts, ideas, and discussions. Notes are the foundation of your
        workflow.
      </p>
      {onCreate && (
        <Button onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Create your first note
        </Button>
      )}
    </div>
  );
}

/**
 * Notes List Page Component
 */
const NotesPage = observer(function NotesPage({ params }: NotesPageProps) {
  const { workspaceSlug } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const workspaceStore = useWorkspaceStore();
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('updated');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filterPinned, setFilterPinned] = useState<boolean | undefined>(undefined);

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

  // Fetch notes with infinite scroll
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } = useInfiniteNotes({
    workspaceId,
    isPinned: filterPinned,
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
      <div className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-6 sm:py-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground sm:text-2xl">Notes</h1>
          <p className="text-sm text-muted-foreground">Your collaborative thinking space</p>
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

      {/* Toolbar */}
      <div className="flex flex-col gap-2 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:gap-4 sm:px-6">
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
          {/* Filter */}
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

          {/* Sort */}
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortBy)}>
            <SelectTrigger className="w-[140px]">
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
