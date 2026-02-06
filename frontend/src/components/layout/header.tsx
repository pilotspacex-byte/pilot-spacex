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
  const workspaceSlug = workspaceStore.currentWorkspace?.slug ?? '';
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

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
    <header className="flex h-10 shrink-0 items-center border-b border-border bg-background px-4">
      {/* Breadcrumb / page context — injected by individual pages */}
    </header>
  );
}
