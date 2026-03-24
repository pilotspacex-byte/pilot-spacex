import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ViewZoneManager } from '../view-zones/ViewZoneManager';

/* ── Mock Monaco editor ──────────────────────────────────────────── */

function createMockEditor() {
  const zones = new Map<
    string,
    { afterLineNumber: number; heightInPx: number; domNode: HTMLDivElement }
  >();
  let nextId = 1;

  const changeViewZones = vi.fn((accessor: (a: unknown) => void) => {
    const changeAccessor = {
      addZone(zone: { afterLineNumber: number; heightInPx: number; domNode: HTMLDivElement }) {
        const id = String(nextId++);
        zones.set(id, zone);
        return id;
      },
      removeZone(id: string) {
        zones.delete(id);
      },
      layoutZone(_id: string) {
        // noop
      },
    };
    accessor(changeAccessor);
  });

  return {
    changeViewZones,
    _zones: zones,
  };
}

/* ── Mock ResizeObserver ─────────────────────────────────────────── */

let resizeObserverInstances: Array<{
  observe: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
  callback: ResizeObserverCallback;
}> = [];

class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    resizeObserverInstances.push(this);
  }
}

beforeEach(() => {
  resizeObserverInstances = [];
  vi.stubGlobal('ResizeObserver', MockResizeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/* ── Tests ───────────────────────────────────────────────────────── */

describe('ViewZoneManager', () => {
  it('addZone returns an HTMLDivElement and tracks zone', () => {
    const editor = createMockEditor();
    const manager = new ViewZoneManager(editor as never);

    const domNode = manager.addZone('block-1', 5, 120);

    expect(domNode).toBeInstanceOf(HTMLDivElement);
    expect(editor.changeViewZones).toHaveBeenCalledOnce();
    expect(manager.getZoneDomNode('block-1')).toBe(domNode);
  });

  it('removeZone removes zone from map and disconnects ResizeObserver', () => {
    const editor = createMockEditor();
    const manager = new ViewZoneManager(editor as never);

    manager.addZone('block-1', 5, 120);
    expect(resizeObserverInstances).toHaveLength(1);

    manager.removeZone('block-1');

    expect(manager.getZoneDomNode('block-1')).toBeUndefined();
    expect(resizeObserverInstances[0]!.disconnect).toHaveBeenCalledOnce();
    // changeViewZones called twice: once for add, once for remove
    expect(editor.changeViewZones).toHaveBeenCalledTimes(2);
  });

  it('removeAll clears all zones', () => {
    const editor = createMockEditor();
    const manager = new ViewZoneManager(editor as never);

    manager.addZone('block-1', 5, 120);
    manager.addZone('block-2', 10, 80);

    manager.removeAll();

    expect(manager.getZoneDomNode('block-1')).toBeUndefined();
    expect(manager.getZoneDomNode('block-2')).toBeUndefined();
    expect(resizeObserverInstances[0]!.disconnect).toHaveBeenCalled();
    expect(resizeObserverInstances[1]!.disconnect).toHaveBeenCalled();
  });

  it('getZoneDomNode returns undefined for unknown blockId', () => {
    const editor = createMockEditor();
    const manager = new ViewZoneManager(editor as never);

    expect(manager.getZoneDomNode('nonexistent')).toBeUndefined();
  });

  it('updatePositions calls editor.changeViewZones to update afterLineNumber', () => {
    const editor = createMockEditor();
    const manager = new ViewZoneManager(editor as never);

    manager.addZone('block-1', 5, 120);
    manager.addZone('block-2', 10, 80);

    editor.changeViewZones.mockClear();

    manager.relayoutAll();

    expect(editor.changeViewZones).toHaveBeenCalledOnce();
  });
});
