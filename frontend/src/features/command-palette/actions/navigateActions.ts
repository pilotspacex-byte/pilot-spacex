import { FileSearch, MoveDown, Hash } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface NavigateActionsContext {
  goToFile?: () => void;
  goToLine?: () => void;
  goToSymbol?: () => void;
}

export function registerNavigateActions(context: NavigateActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'navigate:go-to-file',
      label: 'Go to File',
      category: 'navigate',
      icon: FileSearch,
      shortcut: 'Cmd+P',
      execute: () => context.goToFile?.(),
      priority: 40,
    },
    {
      id: 'navigate:go-to-line',
      label: 'Go to Line',
      category: 'navigate',
      icon: MoveDown,
      shortcut: 'Cmd+G',
      execute: () => context.goToLine?.(),
      priority: 41,
    },
    {
      id: 'navigate:go-to-symbol',
      label: 'Go to Symbol',
      category: 'navigate',
      icon: Hash,
      shortcut: 'Cmd+Shift+O',
      execute: () => context.goToSymbol?.(),
      priority: 42,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
