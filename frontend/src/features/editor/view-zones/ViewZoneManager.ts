import type * as monacoNs from 'monaco-editor';

interface TrackedZone {
  zoneId: string;
  domNode: HTMLDivElement;
  observer: ResizeObserver;
  debounceTimer: ReturnType<typeof setTimeout> | null;
}

/**
 * Manages Monaco view zone lifecycle with ResizeObserver-based height updates.
 *
 * View zones are empty regions injected between editor lines where React
 * components (PM blocks) are rendered via portals. This manager handles:
 * - Creating/removing view zones via Monaco's changeViewZones API
 * - Attaching ResizeObserver to each zone's DOM node for dynamic height
 * - Debounced height updates (50ms) to avoid layout thrashing
 */
export class ViewZoneManager {
  private zones = new Map<string, TrackedZone>();
  private editor: monacoNs.editor.IStandaloneCodeEditor;

  constructor(editor: monacoNs.editor.IStandaloneCodeEditor) {
    this.editor = editor;
  }

  /**
   * Add a view zone after a given line number.
   * Returns the DOM node where React content should be portaled into.
   */
  addZone(blockId: string, afterLineNumber: number, initialHeight: number): HTMLDivElement {
    const domNode = document.createElement('div');
    domNode.style.minHeight = '80px';
    let zoneId = '';

    this.editor.changeViewZones((accessor) => {
      zoneId = accessor.addZone({
        afterLineNumber,
        heightInPx: initialHeight,
        domNode,
        suppressMouseDown: true,
      }) as unknown as string;
    });

    // Debounced ResizeObserver for dynamic height
    const tracked: TrackedZone = { zoneId, domNode, observer: null!, debounceTimer: null };
    const observer = new ResizeObserver((entries) => {
      if (tracked.debounceTimer) clearTimeout(tracked.debounceTimer);
      tracked.debounceTimer = setTimeout(() => {
        tracked.debounceTimer = null;
        const entry = entries[0];
        if (!entry) return;
        this.editor.changeViewZones((accessor) => {
          accessor.layoutZone(zoneId);
        });
      }, 50);
    });
    tracked.observer = observer;

    observer.observe(domNode);

    this.zones.set(blockId, tracked);
    return domNode;
  }

  /**
   * Remove a view zone by block ID.
   * Disconnects the ResizeObserver and removes from Monaco.
   */
  removeZone(blockId: string): void {
    const zone = this.zones.get(blockId);
    if (!zone) return;

    if (zone.debounceTimer) clearTimeout(zone.debounceTimer);
    zone.observer.disconnect();

    this.editor.changeViewZones((accessor) => {
      accessor.removeZone(zone.zoneId);
    });

    this.zones.delete(blockId);
  }

  /** Remove all tracked view zones. */
  removeAll(): void {
    for (const [blockId] of this.zones) {
      this.removeZone(blockId);
    }
  }

  /** Get the DOM node for a view zone, or undefined if not tracked. */
  getZoneDomNode(blockId: string): HTMLDivElement | undefined {
    return this.zones.get(blockId)?.domNode;
  }

  /** Re-layout all zones (triggers height re-measurement from DOM). */
  relayoutAll(): void {
    if (this.zones.size === 0) return;

    this.editor.changeViewZones((accessor) => {
      for (const zone of this.zones.values()) {
        accessor.layoutZone(zone.zoneId);
      }
    });
  }
}
