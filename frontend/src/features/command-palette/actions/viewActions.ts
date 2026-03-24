import { PanelLeft, Eye, List } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface ViewActionsContext {
  toggleSidebar?: () => void;
  togglePreview?: () => void;
  toggleOutline?: () => void;
}

export function registerViewActions(context: ViewActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'view:toggle-sidebar',
      label: 'Toggle Sidebar',
      category: 'view',
      icon: PanelLeft,
      shortcut: 'Cmd+B',
      execute: () => context.toggleSidebar?.(),
      priority: 30,
    },
    {
      id: 'view:toggle-preview',
      label: 'Toggle Preview',
      category: 'view',
      icon: Eye,
      shortcut: 'Cmd+Shift+V',
      execute: () => context.togglePreview?.(),
      priority: 31,
    },
    {
      id: 'view:toggle-outline',
      label: 'Toggle Outline',
      category: 'view',
      icon: List,
      shortcut: 'Cmd+Shift+O',
      execute: () => context.toggleOutline?.(),
      priority: 32,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
