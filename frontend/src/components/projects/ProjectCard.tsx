'use client';

import { motion } from 'motion/react';
import { FolderKanban } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import type { Project } from '@/types';

interface ProjectCardProps {
  project: Project;
  variant?: 'grid' | 'list';
  onClick?: () => void;
  index?: number;
}

function ProgressRing({ progress, size = 32 }: { progress: number; size?: number }) {
  const strokeWidth = 3;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - progress * circumference;

  return (
    <svg width={size} height={size} className="flex-shrink-0 -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-border"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-primary transition-all duration-300"
      />
    </svg>
  );
}

function getInitials(name?: string): string {
  if (!name) return '?';
  return name
    .split(/\s+/)
    .map((w) => w.charAt(0))
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function ProjectCard({ project, variant = 'grid', onClick, index = 0 }: ProjectCardProps) {
  const completedCount = project.issueCount - project.openIssueCount;
  const progress = project.issueCount > 0 ? completedCount / project.issueCount : 0;
  const timeAgo = formatDistanceToNow(new Date(project.updatedAt), { addSuffix: true });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && onClick) {
      e.preventDefault();
      onClick();
    }
  };

  const cardA11y = onClick
    ? {
        role: 'button' as const,
        tabIndex: 0,
        onKeyDown: handleKeyDown,
        'aria-label': `Open project ${project.name}`,
      }
    : {};

  if (variant === 'list') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.03 }}
      >
        <Card
          className={cn(
            'group cursor-pointer transition-all duration-200',
            'hover:shadow-warm-sm hover:bg-accent/30',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'
          )}
          onClick={onClick}
          {...cardA11y}
        >
          <div className="flex items-center gap-4 px-4 py-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 flex-shrink-0">
              {project.icon ? (
                <span className="text-sm">{project.icon}</span>
              ) : (
                <FolderKanban className="h-4 w-4 text-primary" />
              )}
            </div>
            <Badge variant="outline" className="font-mono text-[10px] flex-shrink-0">
              {project.identifier}
            </Badge>
            <span className="font-medium text-sm truncate min-w-0 flex-1">{project.name}</span>
            <span className="text-xs text-muted-foreground truncate max-w-[200px] hidden md:block">
              {project.description}
            </span>
            {project.lead && (
              <Avatar className="h-6 w-6 flex-shrink-0">
                <AvatarFallback className="text-[10px]">
                  {getInitials(project.lead.displayName ?? undefined)}
                </AvatarFallback>
              </Avatar>
            )}
            <div className="flex items-center gap-2 flex-shrink-0">
              {progress > 0 && <ProgressRing progress={progress} size={24} />}
              <span className="text-xs text-muted-foreground tabular-nums">
                {completedCount}/{project.issueCount}
              </span>
            </div>
            <span className="text-xs text-muted-foreground flex-shrink-0 hidden sm:block">
              {timeAgo}
            </span>
          </div>
        </Card>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card
        className={cn(
          'group cursor-pointer transition-all duration-200',
          'hover:shadow-warm-md',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'
        )}
        onClick={onClick}
        {...cardA11y}
      >
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                {project.icon ? (
                  <span className="text-lg">{project.icon}</span>
                ) : (
                  <FolderKanban className="h-5 w-5 text-primary" />
                )}
              </div>
              <div className="min-w-0">
                <Badge variant="outline" className="font-mono text-[10px] mb-1">
                  {project.identifier}
                </Badge>
                <h3 className="text-base font-semibold leading-tight truncate transition-colors group-hover:text-primary">
                  {project.name}
                </h3>
              </div>
            </div>
            {progress > 0 && <ProgressRing progress={progress} />}
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]">
            {project.description || 'No description'}
          </p>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              {project.lead && (
                <Avatar className="h-5 w-5">
                  <AvatarFallback className="text-[9px]">
                    {getInitials(project.lead.displayName ?? undefined)}
                  </AvatarFallback>
                </Avatar>
              )}
              <span className="tabular-nums">
                {completedCount}/{project.issueCount} issues
              </span>
            </div>
            <span>{timeAgo}</span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
