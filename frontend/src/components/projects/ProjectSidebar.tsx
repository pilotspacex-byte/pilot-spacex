'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard,
  ListTodo,
  RefreshCw,
  MessageSquare,
  Settings,
  FolderKanban,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Project } from '@/types';

interface ProjectSidebarProps {
  project: Project;
  workspaceSlug: string;
}

const NAV_ITEMS = [
  { label: 'Overview', icon: LayoutDashboard, segment: 'overview' },
  { label: 'Issues', icon: ListTodo, segment: 'issues' },
  { label: 'Cycles', icon: RefreshCw, segment: 'cycles' },
  { label: 'Chat', icon: MessageSquare, segment: 'chat' },
  { label: 'Settings', icon: Settings, segment: 'settings' },
] as const;

export function ProjectSidebar({ project, workspaceSlug }: ProjectSidebarProps) {
  const pathname = usePathname();
  const basePath = `/${workspaceSlug}/projects/${project.id}`;

  const activeSegment =
    NAV_ITEMS.find((item) => pathname.includes(`${basePath}/${item.segment}`))?.segment ??
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
        <nav className="flex-1 px-2 py-3" aria-label="Project navigation">
          <ul className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
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
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      {/* Mobile tab bar */}
      <nav
        className="md:hidden flex overflow-x-auto border-b border-border px-4 scrollbar-none"
        aria-label="Project navigation"
      >
        {NAV_ITEMS.map((item) => {
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
