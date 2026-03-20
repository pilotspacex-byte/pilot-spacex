import { Bug, CheckSquare, Lightbulb, Wrench } from 'lucide-react';
import type { IssueType } from '@/types';

export const ISSUE_TYPE_CONFIG: Record<
  IssueType,
  { icon: typeof Bug; className: string; label: string }
> = {
  bug: { icon: Bug, className: 'text-red-500', label: 'Bug' },
  feature: { icon: Lightbulb, className: 'text-purple-500', label: 'Feature' },
  improvement: { icon: Wrench, className: 'text-blue-500', label: 'Improvement' },
  task: { icon: CheckSquare, className: 'text-muted-foreground', label: 'Task' },
};
