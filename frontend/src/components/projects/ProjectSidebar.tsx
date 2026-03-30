'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard,
  ListTodo,
  RefreshCw,
  Brain,
  Code2,
  MessageSquare,
  Settings,
  FolderKanban,
  Paperclip,
} from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import type { Project } from '@/types';
import type { WorkspaceFeatureToggles } from '@/types';
import { ProjectNotesPanel } from './ProjectNotesPanel';
import { useWorkspaceStore } from '@/stores';

interface ProjectSidebarProps {
  project: Project;
  workspaceSlug: string;
}

const NAV_ITEMS: readonly {
  label: string;
  icon: typeof LayoutDashboard;
  segment: string;
  badge?: string;
  /** Maps to a WorkspaceFeatureToggles key. Hidden when the feature is disabled. */
  featureKey?: keyof WorkspaceFeatureToggles;
}[] = [
  { label: 'Overview', icon: LayoutDashboard, segment: 'overview' },
  { label: 'Issues', icon: ListTodo, segment: 'issues', featureKey: 'issues' },
  { label: 'Cycles', icon: RefreshCw, segment: 'cycles', featureKey: 'issues' },
  { label: 'Knowledge', icon: Brain, segment: 'knowledge', featureKey: 'knowledge' },
  { label: 'Artifacts', icon: Paperclip, segment: 'artifacts' },
  // TODO: hide Code nav when project has no artifacts AND no connected repo.
  // Project type does not yet expose artifactCount or githubRepoUrl fields.
  // Once those fields are available, filter with: project.artifactCount > 0 || !!project.githubRepoUrl
  { label: 'Code', icon: Code2, segment: 'code' },
  { label: 'Chat', icon: MessageSquare, segment: 'chat', badge: 'Soon', featureKey: 'skills' },
  { label: 'Settings', icon: Settings, segment: 'settings' },
];

export function ProjectSidebarComponent({ project, workspaceSlug }: ProjectSidebarProps) {
  const pathname = usePathname();
  const workspaceStore = useWorkspaceStore();
  const basePath = `/${workspaceSlug}/projects/${project.id}`;

  const visibleNavItems = NAV_ITEMS.filter(
    (item) => !item.featureKey || workspaceStore.isFeatureEnabled(item.featureKey)
  );

  const activeSegment =
    visibleNavItems.find((item) => pathname.includes(`${basePath}/${item.segment}`))?.segment ??
    'overview';

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-56 md:flex-col md:border-r md:border-border">
        {/* Project header */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 flex-shrink-0">
            {project.icon ? (
              <span className="text-base">{project.icon}</span>
            ) : (
              <FolderKanban className="h-4 w-4 text-primary" />
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold truncate">{project.name}</h2>
            <span className="text-[11px] font-mono text-muted-foreground">
              {project.identifier}
            </span>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 overflow-y-auto px-2 py-2" aria-label="Project navigation">
          <ul className="space-y-0.5">
            {visibleNavItems.map((item) => {
              const isActive = activeSegment === item.segment;
              const Icon = item.icon;
              return (
                <li key={item.segment}>
                  <Link
                    href={`${basePath}/${item.segment}`}
                    className={cn(
                      'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors',
                      isActive
                        ? 'bg-accent text-foreground font-medium'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    {item.label}
                    {item.badge && (
                      <span className="ml-auto text-[10px] font-medium text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>

          <Separator className="mx-0 my-2" />
          {workspaceStore.isFeatureEnabled('notes') && (
            <ProjectNotesPanel
              project={project}
              workspaceSlug={workspaceSlug}
              workspaceId={project.workspaceId}
            />
          )}
        </nav>
      </aside>

      {/* Mobile tab bar */}
      <nav
        className="md:hidden flex overflow-x-auto border-b border-border px-4 scrollbar-none"
        aria-label="Project navigation"
      >
        {visibleNavItems.map((item) => {
          const isActive = activeSegment === item.segment;
          const Icon = item.icon;
          return (
            <Link
              key={item.segment}
              href={`${basePath}/${item.segment}`}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors min-w-[44px] min-h-[44px]',
                isActive
                  ? 'border-primary text-foreground font-medium'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              aria-current={isActive ? 'page' : undefined}
              aria-label={item.label}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}

export const ProjectSidebar = observer(ProjectSidebarComponent);
