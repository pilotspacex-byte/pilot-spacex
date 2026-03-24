import { Sparkles, ListChecks } from 'lucide-react';
import { registerAction } from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

interface AiActionsContext {
  toggleGhostText?: () => void;
  extractIssues?: () => void;
}

export function registerAiActions(context: AiActionsContext): () => void {
  const actions: PaletteAction[] = [
    {
      id: 'ai:toggle-ghost-text',
      label: 'Toggle Ghost Text',
      category: 'ai',
      icon: Sparkles,
      execute: () => context.toggleGhostText?.(),
      priority: 70,
    },
    {
      id: 'ai:extract-issues',
      label: 'Extract Issues from Note',
      category: 'ai',
      icon: ListChecks,
      execute: () => context.extractIssues?.(),
      priority: 71,
    },
  ];

  const unregisters = actions.map((a) => registerAction(a));
  return () => unregisters.forEach((fn) => fn());
}
