import type { ActionCategory, PaletteAction } from '../types';

const DEFAULT_PRIORITY = 100;

/** In-memory registry of palette actions. */
let registry = new Map<string, PaletteAction>();

/**
 * Register a palette action. Returns an unregister function.
 * If an action with the same ID already exists, it is overwritten.
 */
export function registerAction(action: PaletteAction): () => void {
  registry.set(action.id, action);
  return () => {
    registry.delete(action.id);
  };
}

/** Remove an action by ID. */
export function unregisterAction(id: string): void {
  registry.delete(id);
}

/** Get all registered actions, sorted by priority (lower first). */
export function getAllActions(): PaletteAction[] {
  return Array.from(registry.values()).sort(
    (a, b) => (a.priority ?? DEFAULT_PRIORITY) - (b.priority ?? DEFAULT_PRIORITY)
  );
}

/** Get actions filtered by category, sorted by priority. */
export function getActionsByCategory(category: ActionCategory): PaletteAction[] {
  return getAllActions().filter((a) => a.category === category);
}

/** Clear all registered actions (primarily for testing). */
export function clearAllActions(): void {
  registry = new Map();
}
