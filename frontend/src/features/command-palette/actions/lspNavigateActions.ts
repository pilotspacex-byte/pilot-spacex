import { Locate, ListTree } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface LSPNavigateActionsContext {
  goToDefinition?: () => void;
  findReferences?: () => void;
}

export function registerLSPNavigateActions(context: LSPNavigateActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'navigate:go-to-definition',
      label: 'Go to Definition',
      category: 'navigate',
      icon: Locate,
      shortcut: 'F12',
      execute: () => context.goToDefinition?.(),
      priority: 43,
    },
    {
      id: 'navigate:find-references',
      label: 'Find All References',
      category: 'navigate',
      icon: ListTree,
      shortcut: 'Shift+F12',
      execute: () => context.findReferences?.(),
      priority: 44,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
