'use client';

/**
 * PresenceSidebarPanel — T-138 (Feature 016 M8)
 *
 * Lists all active editors for the current note.
 * - Human: avatar, name, last edit relative time.
 * - AI skill: skill icon, skill name, current intent reference.
 * - When CRDT not active: "Single-user mode" message.
 * Mounts inside SidebarPanel as content for activePanel="presence".
 */

import { Users, Zap, UserCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface HumanPresenceEntry {
  type: 'human';
  userId: string;
  name: string;
  avatarUrl?: string;
  color: string;
  lastEditAt?: string;
}

export interface AIPresenceEntry {
  type: 'ai_skill';
  skillName: string;
  intentRef?: string;
  skillIcon?: string;
}

export type PresenceEntry = HumanPresenceEntry | AIPresenceEntry;

export interface PresenceSidebarPanelProps {
  /** Active presence entries */
  entries?: PresenceEntry[];
  /** Whether CRDT is enabled for this note */
  crdtActive?: boolean;
  /** Whether loading */
  isLoading?: boolean;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function HumanRow({ entry }: { entry: HumanPresenceEntry }) {
  const timeAgo = entry.lastEditAt
    ? formatDistanceToNow(new Date(entry.lastEditAt), { addSuffix: true })
    : null;

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/40 transition-colors">
      <div className="relative shrink-0">
        <Avatar className="h-7 w-7">
          <AvatarImage src={entry.avatarUrl} alt={entry.name} />
          <AvatarFallback
            className="text-[10px] font-medium"
            style={{ background: `${entry.color}20`, color: entry.color }}
          >
            {getInitials(entry.name)}
          </AvatarFallback>
        </Avatar>
        {/* Online dot */}
        <span
          className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background bg-primary"
          aria-hidden="true"
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{entry.name}</p>
        {timeAgo && <p className="text-xs text-muted-foreground">Edited {timeAgo}</p>}
      </div>
      <Badge variant="outline" className="text-[10px] shrink-0">
        Human
      </Badge>
    </div>
  );
}

function AIRow({ entry }: { entry: AIPresenceEntry }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/40 transition-colors">
      {/* AI skill square icon */}
      <div
        className={cn(
          'h-7 w-7 rounded-sm border-2 border-ai flex items-center justify-center shrink-0',
          'bg-ai/10'
        )}
        aria-hidden="true"
      >
        {entry.skillIcon ? (
          <span className="text-xs">{entry.skillIcon}</span>
        ) : (
          <Zap className="h-3.5 w-3.5 text-ai" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{entry.skillName}</p>
        {entry.intentRef && (
          <p className="text-xs text-muted-foreground truncate">Intent: {entry.intentRef}</p>
        )}
      </div>
      <Badge variant="outline" className="text-[10px] shrink-0 border-ai text-ai">
        AI
      </Badge>
    </div>
  );
}

export function PresenceSidebarPanel({
  entries = [],
  crdtActive = false,
  isLoading = false,
}: PresenceSidebarPanelProps) {
  const humans = entries.filter((e): e is HumanPresenceEntry => e.type === 'human');
  const aiSkills = entries.filter((e): e is AIPresenceEntry => e.type === 'ai_skill');
  const total = entries.length;

  if (!crdtActive) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <UserCircle className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">Single-user mode</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-[200px]">
            Real-time presence requires collaborative editing (CRDT), which is not active for this
            note.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8" aria-label="Loading presence">
        <div
          className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent"
          aria-hidden="true"
        />
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-6 text-center">
        <Users className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">No other editors</p>
        <p className="text-xs text-muted-foreground">You are the only one editing this note.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-3">
      {/* Summary */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
          {total} active {total === 1 ? 'editor' : 'editors'}
        </span>
        {aiSkills.length > 0 && (
          <Badge variant="outline" className="text-[10px] border-ai text-ai">
            {aiSkills.length} AI skill{aiSkills.length !== 1 ? 's' : ''}
          </Badge>
        )}
      </div>

      {/* Humans */}
      {humans.length > 0 && (
        <div role="list" aria-label="Human editors">
          {humans.map((e) => (
            <div key={e.userId} role="listitem">
              <HumanRow entry={e} />
            </div>
          ))}
        </div>
      )}

      {/* Divider */}
      {humans.length > 0 && aiSkills.length > 0 && <hr className="border-border" />}

      {/* AI skills */}
      {aiSkills.length > 0 && (
        <div role="list" aria-label="AI skills editing">
          {aiSkills.map((e) => (
            <div key={e.skillName} role="listitem">
              <AIRow entry={e} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
