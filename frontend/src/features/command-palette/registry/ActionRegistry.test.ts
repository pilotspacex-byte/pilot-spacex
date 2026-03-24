import { describe, it, expect, beforeEach } from 'vitest';
import { File } from 'lucide-react';
import {
  registerAction,
  unregisterAction,
  getAllActions,
  getActionsByCategory,
  clearAllActions,
} from './ActionRegistry';
import type { PaletteAction } from '../types';

function makeAction(overrides: Partial<PaletteAction> = {}): PaletteAction {
  return {
    id: 'test-action',
    label: 'Test Action',
    category: 'file',
    icon: File,
    execute: () => {},
    ...overrides,
  };
}

describe('ActionRegistry', () => {
  beforeEach(() => {
    clearAllActions();
  });

  it('returns empty array when no actions registered', () => {
    expect(getAllActions()).toEqual([]);
  });

  it('registerAction adds action to registry and getAllActions returns it', () => {
    const action = makeAction({ id: 'save', label: 'Save' });
    registerAction(action);
    const all = getAllActions();
    expect(all).toHaveLength(1);
    expect(all[0]!.id).toBe('save');
  });

  it('registerAction returns an unregister function that removes the action', () => {
    const unregister = registerAction(makeAction({ id: 'close' }));
    expect(getAllActions()).toHaveLength(1);
    unregister();
    expect(getAllActions()).toHaveLength(0);
  });

  it('getActionsByCategory returns only actions in that category', () => {
    registerAction(makeAction({ id: 'a1', category: 'file' }));
    registerAction(makeAction({ id: 'a2', category: 'edit' }));
    registerAction(makeAction({ id: 'a3', category: 'file' }));

    const fileActions = getActionsByCategory('file');
    expect(fileActions).toHaveLength(2);
    expect(fileActions.every((a) => a.category === 'file')).toBe(true);
  });

  it('registering action with same ID overwrites previous', () => {
    registerAction(makeAction({ id: 'dup', label: 'Old' }));
    registerAction(makeAction({ id: 'dup', label: 'New' }));
    const all = getAllActions();
    expect(all).toHaveLength(1);
    expect(all[0]!.label).toBe('New');
  });

  it('getAllActions returns actions sorted by priority (lower first)', () => {
    registerAction(makeAction({ id: 'low', priority: 50 }));
    registerAction(makeAction({ id: 'high', priority: 10 }));
    registerAction(makeAction({ id: 'default' })); // no priority = 100

    const all = getAllActions();
    expect(all[0]!.id).toBe('high');
    expect(all[1]!.id).toBe('low');
    expect(all[2]!.id).toBe('default');
  });

  it('unregisterAction removes action by id', () => {
    registerAction(makeAction({ id: 'remove-me' }));
    expect(getAllActions()).toHaveLength(1);
    unregisterAction('remove-me');
    expect(getAllActions()).toHaveLength(0);
  });
});
