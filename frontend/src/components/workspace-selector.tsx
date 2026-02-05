'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import {
  Building2,
  ArrowRight,
  Plus,
  Clock,
  Trash2,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

const WORKSPACE_STORAGE_KEY = 'pilot-space:last-workspace';
const RECENT_WORKSPACES_KEY = 'pilot-space:recent-workspaces';
const MAX_RECENT_WORKSPACES = 5;

interface RecentWorkspace {
  slug: string;
  lastVisited: number;
}

/**
 * Get recent workspaces from localStorage.
 */
function getRecentWorkspaces(): RecentWorkspace[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(RECENT_WORKSPACES_KEY);
    if (stored) {
      return JSON.parse(stored) as RecentWorkspace[];
    }
  } catch {
    // Ignore parse errors
  }
  return [];
}

/**
 * Add a workspace to recent workspaces in localStorage.
 */
export function addRecentWorkspace(slug: string): void {
  if (typeof window === 'undefined') return;
  try {
    const recent = getRecentWorkspaces();
    // Remove if already exists
    const filtered = recent.filter((w) => w.slug !== slug);
    // Add to front
    filtered.unshift({ slug, lastVisited: Date.now() });
    // Keep only max
    const trimmed = filtered.slice(0, MAX_RECENT_WORKSPACES);
    localStorage.setItem(RECENT_WORKSPACES_KEY, JSON.stringify(trimmed));
    localStorage.setItem(WORKSPACE_STORAGE_KEY, slug);
  } catch {
    // Ignore storage errors
  }
}

/**
 * Remove a workspace from recent workspaces.
 */
function removeRecentWorkspace(slug: string): RecentWorkspace[] {
  if (typeof window === 'undefined') return [];
  try {
    const recent = getRecentWorkspaces();
    const filtered = recent.filter((w) => w.slug !== slug);
    localStorage.setItem(RECENT_WORKSPACES_KEY, JSON.stringify(filtered));
    // If removed workspace was last workspace, update to next one
    const lastWorkspace = localStorage.getItem(WORKSPACE_STORAGE_KEY);
    if (lastWorkspace === slug) {
      const nextWorkspace = filtered[0];
      if (nextWorkspace) {
        localStorage.setItem(WORKSPACE_STORAGE_KEY, nextWorkspace.slug);
      } else {
        localStorage.removeItem(WORKSPACE_STORAGE_KEY);
      }
    }
    return filtered;
  } catch {
    return [];
  }
}

/**
 * Format relative time for last visited.
 */
function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

const fadeUp = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

interface WorkspaceSelectorProps {
  onSelect?: (slug: string) => void;
}

export function WorkspaceSelector({ onSelect }: WorkspaceSelectorProps) {
  const router = useRouter();
  const [workspaceSlug, setWorkspaceSlug] = React.useState('');
  const [recentWorkspaces, setRecentWorkspaces] = React.useState<RecentWorkspace[]>([]);
  const [showInput, setShowInput] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Load recent workspaces on mount
  React.useEffect(() => {
    setRecentWorkspaces(getRecentWorkspaces());
  }, []);

  // Focus input when shown
  React.useEffect(() => {
    if (showInput && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showInput]);

  const handleSelectWorkspace = (slug: string) => {
    addRecentWorkspace(slug);
    if (onSelect) {
      onSelect(slug);
    } else {
      router.push(`/${slug}`);
    }
  };

  const handleGoToWorkspace = () => {
    const slug = workspaceSlug.trim().toLowerCase().replace(/\s+/g, '-');
    if (slug) {
      handleSelectWorkspace(slug);
    }
  };

  const handleRemoveWorkspace = (e: React.MouseEvent, slug: string) => {
    e.stopPropagation();
    const updated = removeRecentWorkspace(slug);
    setRecentWorkspaces(updated);
  };

  const hasRecentWorkspaces = recentWorkspaces.length > 0;

  return (
    <div className="w-full max-w-md">
      {/* Recent Workspaces */}
      {hasRecentWorkspaces && !showInput && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-6"
        >
          <div className="mb-3 flex items-center gap-2 px-1">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Recent Workspaces
            </span>
          </div>

          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {recentWorkspaces.map((workspace, index) => (
                <motion.div
                  key={workspace.slug}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20, scale: 0.95 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card
                    className={cn(
                      'group cursor-pointer border-border/50 bg-card/80',
                      'transition-all duration-200',
                      'hover:border-primary/30 hover:bg-card hover:shadow-warm-md'
                    )}
                    onClick={() => handleSelectWorkspace(workspace.slug)}
                  >
                    <CardContent className="flex items-center gap-3 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Building2 className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-foreground truncate">
                          {workspace.slug}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatRelativeTime(workspace.lastVisited)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={(e) => handleRemoveWorkspace(e, workspace.slug)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.div>
      )}

      {/* New Workspace Input */}
      <AnimatePresence mode="wait">
        {(showInput || !hasRecentWorkspaces) && (
          <motion.div
            key="input"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            exit="exit"
          >
            <Card className="border-border/50 bg-card/80 shadow-warm">
              <CardContent className="p-4">
                <div className="flex flex-col gap-3">
                  <div
                    className={cn(
                      'flex items-center gap-3 rounded-lg border border-input bg-background px-3 py-2.5',
                      'focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20'
                    )}
                  >
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <Input
                      ref={inputRef}
                      type="text"
                      value={workspaceSlug}
                      onChange={(e) => setWorkspaceSlug(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleGoToWorkspace()}
                      placeholder="Enter workspace name..."
                      className="flex-1 border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
                    />
                    {workspaceSlug.trim() && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-primary"
                        onClick={handleGoToWorkspace}
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  {hasRecentWorkspaces && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground"
                      onClick={() => {
                        setShowInput(false);
                        setWorkspaceSlug('');
                      }}
                    >
                      Back to recent workspaces
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add New Workspace Button */}
      {hasRecentWorkspaces && !showInput && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-4"
        >
          <Button
            variant="outline"
            className="w-full gap-2 border-dashed"
            onClick={() => setShowInput(true)}
          >
            <Plus className="h-4 w-4" />
            <span>Enter different workspace</span>
          </Button>
        </motion.div>
      )}
    </div>
  );
}
