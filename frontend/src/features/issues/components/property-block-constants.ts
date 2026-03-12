import { Circle, CircleDot, CircleDashed, PlayCircle, CheckCircle2, XCircle } from 'lucide-react';
import { SignalHigh, SignalMedium, SignalLow, AlertTriangle, Minus } from 'lucide-react';

import type { IssueState, IssuePriority } from '@/types';

export const STATE_ICON: Record<
  IssueState,
  { icon: React.ElementType; className: string; label: string }
> = {
  backlog: { icon: CircleDashed, className: 'text-[var(--color-state-backlog)]', label: 'Backlog' },
  todo: { icon: Circle, className: 'text-[var(--color-state-todo)]', label: 'Todo' },
  in_progress: {
    icon: PlayCircle,
    className: 'text-[var(--color-state-in-progress)]',
    label: 'In Progress',
  },
  in_review: {
    icon: CircleDot,
    className: 'text-[var(--color-state-in-review)]',
    label: 'In Review',
  },
  done: { icon: CheckCircle2, className: 'text-[var(--color-state-done)]', label: 'Done' },
  cancelled: {
    icon: XCircle,
    className: 'text-[var(--color-state-cancelled)]',
    label: 'Cancelled',
  },
};

export const PRIORITY_ICON: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string }
> = {
  urgent: {
    icon: AlertTriangle,
    className: 'text-[var(--color-priority-urgent)]',
    label: 'Urgent',
  },
  high: { icon: SignalHigh, className: 'text-[var(--color-priority-high)]', label: 'High' },
  medium: { icon: SignalMedium, className: 'text-[var(--color-priority-medium)]', label: 'Medium' },
  low: { icon: SignalLow, className: 'text-[var(--color-priority-low)]', label: 'Low' },
  none: { icon: Minus, className: 'text-[var(--color-priority-none)]', label: 'None' },
};

export const STATE_GROUP_MAP: Record<string, IssueState> = {
  backlog: 'backlog',
  unstarted: 'todo',
  started: 'in_progress',
  completed: 'done',
  cancelled: 'cancelled',
};
