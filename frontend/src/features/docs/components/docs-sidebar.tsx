'use client';

import Link from 'next/link';
import { useParams, usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { docsNavigation, defaultDocSlug, type DocGroup } from '../lib/docs-registry';

interface DocsSidebarProps {
  className?: string;
}

function SidebarGroup({
  group,
  workspaceSlug,
  activeSlug,
}: {
  group: DocGroup;
  workspaceSlug: string;
  activeSlug: string;
}) {
  return (
    <div className="mb-6">
      <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {group.label}
      </h3>
      <ul className="space-y-0.5">
        {group.items.map((doc) => {
          const isActive = doc.slug === activeSlug;
          return (
            <li key={doc.slug}>
              <Link
                href={`/${workspaceSlug}/docs/${doc.slug}`}
                className={cn(
                  'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 font-medium text-primary'
                    : 'text-foreground/70 hover:bg-muted hover:text-foreground'
                )}
              >
                {isActive && <ChevronRight className="h-3 w-3 shrink-0" />}
                <span className={cn(!isActive && 'pl-5')}>{doc.title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function DocsSidebar({ className }: DocsSidebarProps) {
  const params = useParams();
  const pathname = usePathname();
  const workspaceSlug = (params.workspaceSlug as string) ?? '';

  // Extract active slug from pathname
  const segments = pathname.split('/');
  const docsIndex = segments.indexOf('docs');
  const activeSlug = docsIndex >= 0 ? (segments[docsIndex + 1] ?? defaultDocSlug) : defaultDocSlug;

  return (
    <nav className={cn('w-60 shrink-0 border-r border-border', className)}>
      <div className="sticky top-0 h-full overflow-y-auto p-4">
        <h2 className="mb-4 px-3 text-base font-semibold text-foreground">Documentation</h2>
        {docsNavigation.map((group) => (
          <SidebarGroup
            key={group.label}
            group={group}
            workspaceSlug={workspaceSlug}
            activeSlug={activeSlug}
          />
        ))}
      </div>
    </nav>
  );
}
