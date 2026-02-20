'use client';

import { CheckCircle2, Circle, Loader2, Users } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface ProjectStatsProps {
  totalIssues: number;
  completedIssues: number;
  inProgressIssues: number;
  memberCount: number;
}

const STATS_CONFIG = [
  {
    key: 'total',
    label: 'Total Issues',
    icon: Circle,
    getValue: (s: ProjectStatsProps) => s.totalIssues,
    color: 'text-foreground',
    bg: 'bg-muted/50',
  },
  {
    key: 'completed',
    label: 'Completed',
    icon: CheckCircle2,
    getValue: (s: ProjectStatsProps) => s.completedIssues,
    color: 'text-green-600',
    bg: 'bg-green-50 dark:bg-green-950/30',
  },
  {
    key: 'inProgress',
    label: 'In Progress',
    icon: Loader2,
    getValue: (s: ProjectStatsProps) => s.inProgressIssues,
    color: 'text-amber-600',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
  },
  {
    key: 'members',
    label: 'Members',
    icon: Users,
    getValue: (s: ProjectStatsProps) => s.memberCount,
    color: 'text-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-950/30',
  },
] as const;

export function ProjectStats(props: ProjectStatsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {STATS_CONFIG.map((stat) => {
        const Icon = stat.icon;
        const value = stat.getValue(props);
        return (
          <Card key={stat.key}>
            <CardContent className="flex items-center gap-3 p-4">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg ${stat.bg} flex-shrink-0`}
              >
                <Icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-semibold tabular-nums">{value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
