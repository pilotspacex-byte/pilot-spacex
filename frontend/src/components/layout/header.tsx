'use client';

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import { Search, Bell, Plus, Command, Sparkles, Loader2 } from 'lucide-react';
import { useUIStore, useNotificationStore, useWorkspaceStore } from '@/stores';
import { useCreateNote, createNoteDefaults } from '@/features/notes/hooks';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export const Header = observer(function Header() {
  const router = useRouter();
  const uiStore = useUIStore();
  const notificationStore = useNotificationStore();
  const workspaceStore = useWorkspaceStore();

  // Get workspace context
  const workspaceSlug = workspaceStore.currentWorkspace?.slug || 'pilot-space-demo';
  const workspaceId = workspaceStore.currentWorkspace?.id || workspaceSlug;

  // Create note mutation
  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  // Handler for creating new note
  const handleCreateNote = useCallback(() => {
    createNote.mutate(createNoteDefaults());
  }, [createNote]);

  // Handler for creating new issue
  const handleCreateIssue = useCallback(() => {
    router.push(`/${workspaceSlug}/issues?create=true`);
  }, [router, workspaceSlug]);

  // Handler for creating new project
  const handleCreateProject = useCallback(() => {
    router.push(`/${workspaceSlug}/projects?create=true`);
  }, [router, workspaceSlug]);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background px-4">
      {/* Left: Breadcrumb / Search */}
      <div className="flex items-center gap-4">
        {/* Search Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              onClick={() => uiStore.openSearchModal()}
              className={cn(
                'h-9 w-64 justify-start gap-2 text-muted-foreground',
                'border-input bg-background/50 shadow-warm-sm',
                'hover:bg-accent hover:shadow-warm transition-all'
              )}
            >
              <Search className="h-4 w-4" />
              <span className="flex-1 text-left text-sm">Search...</span>
              <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
                <Command className="h-3 w-3" />K
              </kbd>
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Search notes, issues, and projects</p>
            <p className="text-xs text-muted-foreground">⌘K</p>
          </TooltipContent>
        </Tooltip>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* AI Assistant Toggle */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative text-muted-foreground hover:text-ai"
            >
              <Sparkles className="h-4.5 w-4.5" />
              <motion.span
                className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-ai"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 2 }}
              />
            </Button>
          </TooltipTrigger>
          <TooltipContent>AI Assistant</TooltipContent>
        </Tooltip>

        {/* Quick Create */}
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="default"
                  size="sm"
                  className="gap-1.5 shadow-warm-sm hover:shadow-warm transition-all"
                >
                  <Plus className="h-4 w-4" />
                  <span className="hidden sm:inline">New</span>
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent>Create new...</TooltipContent>
          </Tooltip>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Create New
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="gap-2"
              onClick={handleCreateNote}
              disabled={createNote.isPending}
            >
              {createNote.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <span className="text-base">📄</span>
              )}
              <span>{createNote.isPending ? 'Creating...' : 'Note'}</span>
              <kbd className="ml-auto text-[10px] text-muted-foreground">⌘N</kbd>
            </DropdownMenuItem>
            <DropdownMenuItem className="gap-2" onClick={handleCreateIssue}>
              <span className="text-base">🐛</span>
              <span>Issue</span>
              <kbd className="ml-auto text-[10px] text-muted-foreground">C</kbd>
            </DropdownMenuItem>
            <DropdownMenuItem className="gap-2" onClick={handleCreateProject}>
              <span className="text-base">📁</span>
              <span>Project</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Notifications */}
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative text-muted-foreground">
                  <Bell className="h-4.5 w-4.5" />
                  {notificationStore.unreadCount > 0 && (
                    <Badge
                      variant="destructive"
                      className="absolute -right-1 -top-1 h-4 min-w-4 px-1 text-[10px]"
                    >
                      {notificationStore.unreadCount}
                    </Badge>
                  )}
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent>Notifications</TooltipContent>
          </Tooltip>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Notifications</span>
              {notificationStore.unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto px-2 py-1 text-xs text-primary"
                  onClick={() => notificationStore.markAllAsRead()}
                >
                  Mark all read
                </Button>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="max-h-80 overflow-y-auto">
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Bell className="mb-2 h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No notifications yet</p>
                <p className="text-xs text-muted-foreground/70">You&apos;ll see updates here</p>
              </div>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8 border border-border">
                <AvatarImage src="" alt="User" />
                <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                  TD
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium">Tin Dang</p>
                <p className="text-xs text-muted-foreground">tin@pilotspace.dev</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuItem>Keyboard shortcuts</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
});
