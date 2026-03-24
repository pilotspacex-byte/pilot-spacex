import type React from 'react';

export type ActionCategory = 'file' | 'edit' | 'view' | 'navigate' | 'note' | 'ai';

export interface PaletteAction {
  id: string;
  label: string;
  category: ActionCategory;
  icon: React.ComponentType<{ className?: string }>;
  shortcut?: string; // Display string e.g. "Cmd+S"
  execute: () => void;
  priority?: number; // Lower = higher priority (default: 100)
}
