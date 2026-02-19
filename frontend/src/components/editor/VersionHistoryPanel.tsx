'use client';

/**
 * VersionHistoryPanel - Chronological version list with diff view
 * Preview without restore, restore with confirmation
 */
import { useCallback, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import { formatDistanceToNow, format } from 'date-fns';
import {
  History,
  Clock,
  Eye,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  FileText,
  User as UserIcon,
  Sparkles,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import type { User, NoteContent } from '@/types';

export interface NoteVersion {
  id: string;
  versionNumber: number;
  content: NoteContent;
  wordCount: number;
  createdAt: string;
  createdBy?: User | string | null;
  changeDescription?: string;
  /** Whether this version includes AI-assisted edits */
  isAIAssisted?: boolean;
}

export interface VersionHistoryPanelProps {
  /** List of versions, newest first */
  versions: NoteVersion[];
  /** Current version ID */
  currentVersionId?: string;
  /** Whether loading versions */
  isLoading?: boolean;
  /** Callback to preview version */
  onPreview?: (version: NoteVersion) => void;
  /** Callback to restore version */
  onRestore: (version: NoteVersion) => Promise<void>;
  /** Callback to compare versions */
  onCompare?: (versionA: NoteVersion, versionB: NoteVersion) => void;
}

/**
 * Get user initials for avatar fallback
 */
function getInitials(name?: string | null): string {
  if (!name) return '?';
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getCreatedByName(createdBy?: User | string | null): string | undefined {
  if (!createdBy) return undefined;
  if (typeof createdBy === 'string') return undefined;
  return createdBy.name;
}

function getCreatedByAvatar(createdBy?: User | string | null): string | undefined {
  if (!createdBy || typeof createdBy === 'string') return undefined;
  return createdBy.avatarUrl;
}

/**
 * Single version item
 */
function VersionItem({
  version,
  isCurrent,
  isSelected,
  onSelect,
  onPreview,
  onRestore,
}: {
  version: NoteVersion;
  isCurrent: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onPreview?: () => void;
  onRestore: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const timeAgo = formatDistanceToNow(new Date(version.createdAt), { addSuffix: true });
  const fullDate = format(new Date(version.createdAt), 'PPp');

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'group rounded-lg border p-3 transition-all cursor-pointer',
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50 hover:bg-accent/50'
      )}
      onClick={onSelect}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Avatar className="h-6 w-6">
            <AvatarImage src={getCreatedByAvatar(version.createdBy)} alt={getCreatedByName(version.createdBy) ?? 'User'} />
            <AvatarFallback className="text-[10px]">
              {getInitials(getCreatedByName(version.createdBy))}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-foreground">
                Version {version.versionNumber}
              </span>
              {isCurrent && (
                <Badge variant="default" className="text-[10px]">
                  Current
                </Badge>
              )}
              {version.isAIAssisted && (
                <Badge
                  variant="outline"
                  className="text-[10px] gap-1 bg-ai-muted border-ai-border text-ai"
                >
                  <Sparkles className="h-3 w-3" />
                  You + AI
                </Badge>
              )}
            </div>
            <span className="text-xs text-muted-foreground">{timeAgo}</span>
          </div>
        </div>

        <Button
          variant="ghost"
          size="icon-sm"
          className="h-6 w-6 opacity-0 group-hover:opacity-100"
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>

      {/* Expanded details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-border space-y-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <UserIcon className="h-3 w-3" />
                {getCreatedByName(version.createdBy) ?? 'Unknown'}
                {version.isAIAssisted && <span className="text-ai">+ Pilot AI</span>}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {fullDate}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <FileText className="h-3 w-3" />
                {version.wordCount.toLocaleString()} words
              </div>
              {version.changeDescription && (
                <p className="text-xs text-muted-foreground italic">
                  &ldquo;{version.changeDescription}&rdquo;
                </p>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2">
                {onPreview && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onPreview();
                    }}
                  >
                    <Eye className="mr-1.5 h-3.5 w-3.5" />
                    Preview
                  </Button>
                )}
                {!isCurrent && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRestore();
                    }}
                  >
                    <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
                    Restore
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/**
 * Empty state when no versions
 */
function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
        <History className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="font-medium text-foreground mb-1">No version history</h3>
      <p className="text-sm text-muted-foreground max-w-[200px]">
        Version history will appear here as you save changes to your note.
      </p>
    </div>
  );
}

/**
 * VersionHistoryPanel component
 */
export const VersionHistoryPanel = observer(function VersionHistoryPanel({
  versions,
  currentVersionId,
  isLoading = false,
  onPreview,
  onRestore,
  onCompare: _onCompare,
}: VersionHistoryPanelProps) {
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [restoreVersion, setRestoreVersion] = useState<NoteVersion | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  const handleRestore = useCallback(async () => {
    if (!restoreVersion) return;

    setIsRestoring(true);
    try {
      await onRestore(restoreVersion);
      setRestoreVersion(null);
    } finally {
      setIsRestoring(false);
    }
  }, [restoreVersion, onRestore]);

  if (versions.length === 0 && !isLoading) {
    return <EmptyState />;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Version History</span>
        </div>
        <Badge variant="secondary" className="text-[10px]">
          {versions.length} versions
        </Badge>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}

      {/* Versions list */}
      <ScrollArea className="flex-1">
        <div className="space-y-2 p-3">
          <AnimatePresence mode="popLayout">
            {versions.map((version, index) => {
              const isCurrent = version.id === currentVersionId || index === 0;
              return (
                <VersionItem
                  key={version.id}
                  version={version}
                  isCurrent={isCurrent}
                  isSelected={selectedVersionId === version.id}
                  onSelect={() => setSelectedVersionId(version.id)}
                  onPreview={onPreview ? () => onPreview(version) : undefined}
                  onRestore={() => setRestoreVersion(version)}
                />
              );
            })}
          </AnimatePresence>
        </div>
      </ScrollArea>

      {/* Restore confirmation dialog */}
      <Dialog open={!!restoreVersion} onOpenChange={() => setRestoreVersion(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Restore version</DialogTitle>
            <DialogDescription>
              Are you sure you want to restore to Version {restoreVersion?.versionNumber}? This will
              create a new version with the restored content.
            </DialogDescription>
          </DialogHeader>
          {restoreVersion && (
            <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/30 p-3">
              <Avatar className="h-8 w-8">
                <AvatarImage
                  src={getCreatedByAvatar(restoreVersion.createdBy)}
                  alt={getCreatedByName(restoreVersion.createdBy) ?? 'User'}
                />
                <AvatarFallback>{getInitials(getCreatedByName(restoreVersion.createdBy))}</AvatarFallback>
              </Avatar>
              <div>
                <p className="text-sm font-medium">Version {restoreVersion.versionNumber}</p>
                <p className="text-xs text-muted-foreground">
                  {format(new Date(restoreVersion.createdAt), 'PPp')}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreVersion(null)}>
              Cancel
            </Button>
            <Button onClick={handleRestore} disabled={isRestoring}>
              {isRestoring ? 'Restoring...' : 'Restore'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
});

export default VersionHistoryPanel;
