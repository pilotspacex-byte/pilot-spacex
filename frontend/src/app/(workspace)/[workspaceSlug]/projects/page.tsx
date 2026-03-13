'use client';

import { useState, useMemo, useCallback, useSyncExternalStore } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Plus, LayoutGrid, List, Search, AlertCircle, FolderKanban } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useProjects, selectAllProjects } from '@/features/projects/hooks';
import { useWorkspaceStore } from '@/stores/RootStore';
import { ProjectCard } from '@/components/projects/ProjectCard';
import { ProjectCardSkeleton } from '@/components/projects/ProjectCardSkeleton';
import { CreateProjectModal } from '@/components/projects/CreateProjectModal';
import type { Project } from '@/types';

type SortOption = 'recent' | 'name' | 'issues' | 'progress';
type ViewMode = 'grid' | 'list';

const VIEW_MODE_KEY = 'projects-view-mode';

function subscribeToViewMode(callback: () => void) {
  const handler = (e: StorageEvent) => {
    if (e.key === VIEW_MODE_KEY) callback();
  };
  window.addEventListener('storage', handler);
  return () => window.removeEventListener('storage', handler);
}

function getViewModeSnapshot(): ViewMode {
  return (localStorage.getItem(VIEW_MODE_KEY) as ViewMode) || 'grid';
}

function getViewModeServerSnapshot(): ViewMode {
  return 'grid';
}

function sortProjects(projects: Project[], sortBy: SortOption): Project[] {
  const sorted = [...projects];
  switch (sortBy) {
    case 'recent':
      return sorted.sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    case 'name':
      return sorted.sort((a, b) => a.name.localeCompare(b.name));
    case 'issues':
      return sorted.sort((a, b) => b.issueCount - a.issueCount);
    case 'progress': {
      const pct = (p: Project) =>
        p.issueCount > 0 ? (p.issueCount - p.openIssueCount) / p.issueCount : 0;
      return sorted.sort((a, b) => pct(a) - pct(b));
    }
  }
}

export default function ProjectsPage() {
  const params = useParams<{ workspaceSlug: string }>();
  const router = useRouter();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';
  const isAdmin = workspaceStore.isAdmin;

  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('recent');
  const [leadFilter, setLeadFilter] = useState<string>('all');
  const viewMode = useSyncExternalStore(
    subscribeToViewMode,
    getViewModeSnapshot,
    getViewModeServerSnapshot
  );
  const handleViewModeChange = useCallback((mode: ViewMode) => {
    localStorage.setItem(VIEW_MODE_KEY, mode);
    // Force re-render since useSyncExternalStore only triggers on storage events from other tabs
    window.dispatchEvent(new StorageEvent('storage', { key: VIEW_MODE_KEY }));
  }, []);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const { data, isLoading, isError, refetch } = useProjects({
    workspaceId,
    enabled: !!workspaceId,
  });

  const allProjects = useMemo(() => selectAllProjects(data), [data]);

  const filteredProjects = useMemo(() => {
    let result = allProjects;

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description?.toLowerCase().includes(q) ||
          p.identifier.toLowerCase().includes(q)
      );
    }

    if (leadFilter !== 'all') {
      result = result.filter((p) => p.leadId === leadFilter);
    }

    return sortProjects(result, sortBy);
  }, [allProjects, search, leadFilter, sortBy]);

  const leads = useMemo(() => {
    const uniqueLeads = new Map<string, string>();
    for (const p of allProjects) {
      if (p.leadId && p.lead) {
        uniqueLeads.set(p.leadId, p.lead.displayName ?? p.leadId);
      }
    }
    return Array.from(uniqueLeads.entries());
  }, [allProjects]);

  const handleCardClick = useCallback(
    (project: Project) => {
      router.push(`/${params.workspaceSlug}/projects/${project.id}`);
    },
    [router, params.workspaceSlug]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-4 sm:px-6">
        <div>
          <h1 className="text-xl font-semibold text-foreground sm:text-2xl">Projects</h1>
          <p className="text-sm text-muted-foreground">
            {allProjects.length} project{allProjects.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border p-1">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon-sm"
              className="h-7 w-7"
              onClick={() => handleViewModeChange('grid')}
              aria-label="Grid view"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon-sm"
              className="h-7 w-7"
              onClick={() => handleViewModeChange('list')}
              aria-label="List view"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
          {isAdmin && (
            <Button className="gap-2 shadow-warm-sm" onClick={() => setCreateModalOpen(true)}>
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">New Project</span>
              <span className="sm:hidden">New</span>
            </Button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-2 border-b border-border/50 px-4 py-2 sm:flex-row sm:items-center sm:gap-4 sm:px-6">
        <div className="relative sm:flex-1 sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            aria-label="Search projects"
          />
        </div>
        <div className="flex items-center gap-2">
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-[140px] sm:w-[160px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Most Recent</SelectItem>
              <SelectItem value="name">Name (A-Z)</SelectItem>
              <SelectItem value="issues">Most Issues</SelectItem>
              <SelectItem value="progress">Least Progress</SelectItem>
            </SelectContent>
          </Select>
          {leads.length > 0 && (
            <Select value={leadFilter} onValueChange={setLeadFilter}>
              <SelectTrigger className="w-[130px] sm:w-[160px]">
                <SelectValue placeholder="Filter by lead" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Leads</SelectItem>
                {leads.map(([id, name]) => (
                  <SelectItem key={id} value={id}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 sm:p-6">
        {isLoading ? (
          <div
            className={
              viewMode === 'grid'
                ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3'
                : 'flex flex-col gap-2'
            }
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <ProjectCardSkeleton key={i} variant={viewMode} />
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <AlertCircle className="h-10 w-10 text-destructive mb-3" />
            <h3 className="text-lg font-medium">Failed to load projects</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Something went wrong while fetching your projects.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              Try Again
            </Button>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <FolderKanban className="h-10 w-10 text-muted-foreground/50 mb-3" />
            <h3 className="text-lg font-medium">
              {search || leadFilter !== 'all' ? 'No matching projects' : 'No projects yet'}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {search || leadFilter !== 'all'
                ? 'Try adjusting your search or filters.'
                : 'Create your first project to get started.'}
            </p>
            {!search && leadFilter === 'all' && isAdmin && (
              <Button onClick={() => setCreateModalOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Create your first project
              </Button>
            )}
          </div>
        ) : (
          <div
            className={
              viewMode === 'grid'
                ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3'
                : 'flex flex-col gap-2'
            }
          >
            {filteredProjects.map((project, index) => (
              <ProjectCard
                key={project.id}
                project={project}
                variant={viewMode}
                index={index}
                onClick={() => handleCardClick(project)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      <CreateProjectModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        workspaceId={workspaceId}
      />
    </div>
  );
}
