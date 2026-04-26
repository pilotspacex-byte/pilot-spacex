/**
 * CommandPalette responsive width tests — Phase 94 Plan 02 (MIG-03).
 *
 * Verifies the dialog content className branches:
 *  - Carries `w-[95vw]` (mobile-first base)
 *  - Carries `md:w-[680px]` (≥768 fixed width preserved)
 *  - Carries `md:max-w-[680px]` cap so the dialog never overflows on tablet+
 *
 * Also asserts the scope-tabs row uses `flex-wrap` so the 7 scope buttons
 * reflow without horizontal scroll at <425.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { makeAutoObservable } from 'mobx';

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  } as unknown as typeof ResizeObserver;
}

class TestUIStore {
  commandPaletteOpen = true;
  paletteScope = 'all' as const;
  palettePrefixMode: null | 'tasks' | 'people' | 'pages' | 'commands' = null;
  paletteMode: null | 'search' | 'move' = null;
  paletteMoveSourceId: string | null = null;
  paletteMoveSourceParentId: string | null = null;
  constructor() {
    makeAutoObservable(this);
  }
  openCommandPalette(): void {
    this.commandPaletteOpen = true;
  }
  closeCommandPalette(): void {
    this.commandPaletteOpen = false;
  }
  setPaletteScope(): void {}
  setPalettePrefixMode(): void {}
}

class TestWorkspaceStore {
  currentWorkspaceId = 'ws-1';
  currentWorkspace = { id: 'ws-1', slug: 'alpha', name: 'Alpha' };
  constructor() {
    makeAutoObservable(this);
  }
  getWorkspaceBySlug() {
    return this.currentWorkspace;
  }
}

const stub = {
  uiStore: new TestUIStore(),
  workspaceStore: new TestWorkspaceStore(),
};

vi.mock('@/stores', () => ({
  useUIStore: () => stub.uiStore,
  useWorkspaceStore: () => stub.workspaceStore,
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ workspaceSlug: 'alpha' }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/alpha',
}));

vi.mock('@/services/api/notes', () => ({
  notesApi: { list: vi.fn().mockResolvedValue({ items: [] }) },
}));
vi.mock('@/services/api/issues', () => ({
  issuesApi: { list: vi.fn().mockResolvedValue({ items: [] }) },
}));
vi.mock('@/features/skills/hooks', () => ({
  useSkillCatalog: () => ({ data: [] }),
}));
vi.mock('@/features/topics/components', () => ({
  MoveToPickerContent: () => null,
}));
vi.mock('@/hooks/usePaletteQueryStringSync', () => ({
  usePaletteQueryStringSync: () => undefined,
}));

import { CommandPalette } from '../CommandPalette';

describe('CommandPalette — responsive width (MIG-03)', () => {
  it('dialog content className includes 95vw base + md:680px', () => {
    render(<CommandPalette />);
    // Radix Dialog mounts the Content via Portal; we locate by role=dialog.
    const dialogs = screen.getAllByRole('dialog');
    // Find the cmdk dialog — has the rounded-[20px] palette class.
    const palette = dialogs.find((d) => d.className.includes('rounded-[20px]'));
    expect(palette).toBeDefined();
    expect(palette!.className).toMatch(/w-\[95vw\]/);
    expect(palette!.className).toMatch(/md:w-\[680px\]/);
    expect(palette!.className).toMatch(/md:max-w-\[680px\]/);
  });

  it('scope tabs row uses flex-wrap so buttons reflow at <425', () => {
    render(<CommandPalette />);
    const tablist = screen.getByRole('tablist', { name: /palette scope/i });
    expect(tablist.className).toMatch(/flex-wrap/);
  });
});
