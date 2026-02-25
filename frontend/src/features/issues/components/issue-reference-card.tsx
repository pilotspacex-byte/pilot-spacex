'use client';

import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

interface IssueReferenceCardProps {
  issueId: string;
  identifier: string;
  title: string;
  stateGroup: string; // 'unstarted' | 'started' | 'completed' | 'cancelled'
  relationType: 'blocks' | 'blocked_by' | 'relates';
  workspaceSlug: string;
}

const STATE_GROUP_DOT: Record<string, string> = {
  unstarted: 'bg-gray-400',
  started: 'bg-amber-400',
  completed: 'bg-green-500',
  cancelled: 'bg-red-400',
};

const RELATION_TYPE_CHIP: Record<IssueReferenceCardProps['relationType'], string> = {
  blocks: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  blocked_by: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  relates: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
};

const RELATION_TYPE_LABEL: Record<IssueReferenceCardProps['relationType'], string> = {
  blocks: 'blocks',
  blocked_by: 'blocked by',
  relates: 'relates',
};

export function IssueReferenceCard({
  issueId,
  identifier,
  title,
  stateGroup,
  relationType,
  workspaceSlug,
}: IssueReferenceCardProps) {
  const router = useRouter();
  const dotClass = STATE_GROUP_DOT[stateGroup] ?? 'bg-gray-400';

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/${workspaceSlug}/issues/${issueId}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          router.push(`/${workspaceSlug}/issues/${issueId}`);
        }
      }}
      className={cn(
        'border border-border rounded-lg p-2.5 flex items-center gap-2',
        'hover:bg-muted/50 cursor-pointer transition-colors'
      )}
    >
      <span className={cn('h-3 w-3 rounded-full shrink-0', dotClass)} aria-hidden="true" />
      <span className="font-mono text-xs text-primary shrink-0">{identifier}</span>
      <span className="flex-1 text-sm truncate">{title}</span>
      <span
        className={cn(
          'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
          RELATION_TYPE_CHIP[relationType]
        )}
      >
        {RELATION_TYPE_LABEL[relationType]}
      </span>
    </div>
  );
}
