import { File, Save, X, XCircle } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface FileActionsContext {
  saveFile?: () => void;
  closeTab?: () => void;
  closeAllTabs?: () => void;
  newFile?: () => void;
}

export function registerFileActions(context: FileActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'file:new',
      label: 'New File',
      category: 'file',
      icon: File,
      execute: () => context.newFile?.(),
      priority: 10,
    },
    {
      id: 'file:save',
      label: 'Save',
      category: 'file',
      icon: Save,
      shortcut: 'Cmd+S',
      execute: () => context.saveFile?.(),
      priority: 11,
    },
    {
      id: 'file:close-tab',
      label: 'Close Tab',
      category: 'file',
      icon: X,
      shortcut: 'Cmd+W',
      execute: () => context.closeTab?.(),
      priority: 12,
    },
    {
      id: 'file:close-all',
      label: 'Close All Tabs',
      category: 'file',
      icon: XCircle,
      execute: () => context.closeAllTabs?.(),
      priority: 13,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
