'use client';

import { observer } from 'mobx-react-lite';
import { motion } from 'motion/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useMemo } from 'react';
import {
  Home,
  FileText,
  LayoutGrid,
  FolderKanban,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  Compass,
  PinIcon,
  Clock,
  Loader2,
} from 'lucide-react';
import { useUIStore, useWorkspaceStore, useNoteStore } from '@/stores';
import { useCreateNote, createNoteDefaults } from '@/features/notes/hooks';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// Navigation items - paths are relative and will be prefixed with workspace slug
const navigationItems = [
  { name: 'Home', path: '', icon: Home, testId: 'nav-home' },
  { name: 'Notes', path: 'notes', icon: FileText, testId: 'nav-notes' },
  { name: 'Issues', path: 'issues', icon: LayoutGrid, testId: 'nav-issues' },
  { name: 'Projects', path: 'projects', icon: FolderKanban, testId: 'nav-projects' },
];

export const Sidebar = observer(function Sidebar() {
  const uiStore = useUIStore();
  const workspaceStore = useWorkspaceStore();
  const noteStore = useNoteStore();
  const pathname = usePathname();
  const router = useRouter();
  const collapsed = uiStore.sidebarCollapsed;

  // Get workspace slug from store or use default
  const workspaceSlug = workspaceStore.currentWorkspace?.slug || 'pilot-space-demo';
  const workspaceId = workspaceStore.currentWorkspace?.id || workspaceSlug;

  // Create note mutation
  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  // Build navigation with workspace prefix
  const navigation = useMemo(() => {
    return navigationItems.map((item) => ({
      ...item,
      href: item.path ? `/${workspaceSlug}/${item.path}` : `/${workspaceSlug}`,
    }));
  }, [workspaceSlug]);

  // Build pinned notes links from store
  const pinnedNotes = useMemo(() => {
    return noteStore.pinnedNotes.slice(0, 5).map((note) => ({
      id: note.id,
      title: note.title,
      href: `/${workspaceSlug}/notes/${note.id}`,
    }));
  }, [noteStore.pinnedNotes, workspaceSlug]);

  // Build recent notes links from store
  const recentNotes = useMemo(() => {
    return noteStore.recentNotes
      .filter((note) => !noteStore.pinnedNotes.some((p) => p.id === note.id))
      .slice(0, 5)
      .map((note) => ({
        id: note.id,
        title: note.title,
        href: `/${workspaceSlug}/notes/${note.id}`,
      }));
  }, [noteStore.recentNotes, noteStore.pinnedNotes, workspaceSlug]);

  // Handle new note creation
  const handleNewNote = useCallback(() => {
    createNote.mutate(createNoteDefaults());
  }, [createNote]);

  return (
    <div className="flex h-full flex-col">
      {/* Logo & Workspace */}
      <div className="flex h-14 items-center gap-3 border-b border-sidebar-border px-4">
        <motion.div
          whileHover={{ rotate: 15 }}
          transition={{ type: 'spring', stiffness: 400, damping: 10 }}
        >
          <Compass className="h-6 w-6 text-primary" />
        </motion.div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="flex flex-col"
          >
            <span className="text-sm font-semibold text-sidebar-foreground">Pilot Space</span>
            <span className="text-xs text-muted-foreground">Workspace</span>
          </motion.div>
        )}
      </div>

      {/* Main Navigation */}
      <div className="flex flex-col gap-1 p-3">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Tooltip key={item.name} delayDuration={collapsed ? 0 : 1000}>
              <TooltipTrigger asChild>
                <Link
                  href={item.href}
                  data-testid={item.testId}
                  className={cn(
                    'group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-primary shadow-warm-sm'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50',
                    collapsed && 'justify-center px-2'
                  )}
                >
                  <item.icon
                    className={cn(
                      'h-4.5 w-4.5 shrink-0 transition-colors',
                      isActive
                        ? 'text-sidebar-primary'
                        : 'text-muted-foreground group-hover:text-sidebar-foreground'
                    )}
                  />
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {item.name}
                    </motion.span>
                  )}
                </Link>
              </TooltipTrigger>
              {collapsed && (
                <TooltipContent side="right" className="font-medium">
                  {item.name}
                </TooltipContent>
              )}
            </Tooltip>
          );
        })}
      </div>

      <Separator className="mx-3" />

      {/* Notes sections */}
      <ScrollArea className="flex-1 px-3 py-2">
        {!collapsed && (
          <>
            {/* Pinned Notes */}
            <div className="mb-4" data-testid="pinned-notes">
              <div className="mb-2 flex items-center gap-2 px-2">
                <PinIcon className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Pinned
                </span>
              </div>
              <div className="space-y-0.5">
                {pinnedNotes.map((note, index) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Link
                      href={note.href}
                      data-testid="note-item"
                      className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent/50"
                    >
                      <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="truncate">{note.title}</span>
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Recent Notes */}
            <div data-testid="note-list">
              <div className="mb-2 flex items-center gap-2 px-2">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Recent
                </span>
              </div>
              <div className="space-y-0.5">
                {recentNotes.map((note, index) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 + 0.1 }}
                  >
                    <Link
                      href={note.href}
                      data-testid="note-item"
                      className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span className="truncate">{note.title}</span>
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>
          </>
        )}
      </ScrollArea>

      {/* New Note Button */}
      <div className="border-t border-sidebar-border p-3">
        <Tooltip delayDuration={collapsed ? 0 : 1000}>
          <TooltipTrigger asChild>
            <Button
              variant="default"
              size={collapsed ? 'icon' : 'default'}
              data-testid="new-note-button"
              onClick={handleNewNote}
              disabled={createNote.isPending}
              className={cn(
                'w-full shadow-warm-sm transition-all duration-200',
                'hover:shadow-warm-md hover:-translate-y-0.5',
                collapsed && 'h-9 w-9'
              )}
            >
              {createNote.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              {!collapsed && (
                <span className="ml-2">{createNote.isPending ? 'Creating...' : 'New Note'}</span>
              )}
            </Button>
          </TooltipTrigger>
          {collapsed && <TooltipContent side="right">New Note</TooltipContent>}
        </Tooltip>
      </div>

      {/* Collapse Toggle */}
      <div className="border-t border-sidebar-border p-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => uiStore.toggleSidebar()}
              className={cn(
                'w-full justify-center text-muted-foreground hover:text-sidebar-foreground',
                collapsed && 'px-2'
              )}
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side={collapsed ? 'right' : 'top'}>
            {collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          </TooltipContent>
        </Tooltip>
      </div>

      {/* Settings */}
      {!collapsed && (
        <div className="border-t border-sidebar-border p-3">
          <Link
            href={`/${workspaceSlug}/settings`}
            data-testid="nav-settings"
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
          >
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Link>
        </div>
      )}
    </div>
  );
});
