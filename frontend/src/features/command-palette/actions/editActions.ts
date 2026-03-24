import { Undo2, Redo2, Search, Replace } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface EditActionsContext {
  undo?: () => void;
  redo?: () => void;
  find?: () => void;
  replace?: () => void;
}

export function registerEditActions(context: EditActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'edit:undo',
      label: 'Undo',
      category: 'edit',
      icon: Undo2,
      shortcut: 'Cmd+Z',
      execute: () => context.undo?.(),
      priority: 20,
    },
    {
      id: 'edit:redo',
      label: 'Redo',
      category: 'edit',
      icon: Redo2,
      shortcut: 'Cmd+Shift+Z',
      execute: () => context.redo?.(),
      priority: 21,
    },
    {
      id: 'edit:find',
      label: 'Find',
      category: 'edit',
      icon: Search,
      shortcut: 'Cmd+F',
      execute: () => context.find?.(),
      priority: 22,
    },
    {
      id: 'edit:replace',
      label: 'Replace',
      category: 'edit',
      icon: Replace,
      shortcut: 'Cmd+H',
      execute: () => context.replace?.(),
      priority: 23,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
