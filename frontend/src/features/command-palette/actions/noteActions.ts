import {
  LayoutDashboard,
  AlertTriangle,
  GitBranch,
  Clock,
  Columns,
  BarChart3,
  FileText,
  ScrollText,
  Users,
  Focus,
} from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface NoteActionsContext {
  insertPMBlock?: (type: string) => void;
  toggleFocusMode?: () => void;
}

export function registerNoteActions(context: NoteActionsContext): () => void {
  const pmBlocks: Array<{ type: string; label: string; icon: typeof LayoutDashboard }> = [
    { type: 'decision', label: 'Insert PM Block: Decision', icon: LayoutDashboard },
    { type: 'risk', label: 'Insert PM Block: Risk', icon: AlertTriangle },
    { type: 'dependency', label: 'Insert PM Block: Dependency', icon: GitBranch },
    { type: 'timeline', label: 'Insert PM Block: Timeline', icon: Clock },
    { type: 'sprint-board', label: 'Insert PM Block: Sprint Board', icon: Columns },
    { type: 'dashboard', label: 'Insert PM Block: Dashboard', icon: BarChart3 },
    { type: 'form', label: 'Insert PM Block: Form', icon: FileText },
    { type: 'release-notes', label: 'Insert PM Block: Release Notes', icon: ScrollText },
    { type: 'raci', label: 'Insert PM Block: RACI', icon: Users },
    { type: 'capacity-plan', label: 'Insert PM Block: Capacity Plan', icon: BarChart3 },
  ];

  const actions: PaletteAction[] = [
    ...pmBlocks.map((block, idx) => ({
      id: `note:pm-${block.type}`,
      label: block.label,
      category: 'note' as const,
      icon: block.icon,
      execute: () => context.insertPMBlock?.(block.type),
      priority: 50 + idx,
    })),
    {
      id: 'note:focus-mode',
      label: 'Toggle Focus Mode',
      category: 'note' as const,
      icon: Focus,
      execute: () => context.toggleFocusMode?.(),
      priority: 60,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
