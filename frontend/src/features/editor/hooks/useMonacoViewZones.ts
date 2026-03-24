'use client';

import React, { useEffect, useRef, useState, useMemo, type ReactPortal } from 'react';
import { createPortal } from 'react-dom';
import type * as monacoNs from 'monaco-editor';
import { parsePMBlockMarkers } from '../markers/pmBlockMarkers';
import { ViewZoneManager } from '../view-zones/ViewZoneManager';
import { PMBlockViewZone } from '../view-zones/PMBlockViewZone';

/**
 * Hook managing PM block view zones with React portals.
 *
 * Parses PM block markers from content, creates Monaco view zones for each,
 * and returns React portals to render PM block components into the zone DOM nodes.
 *
 * IMPORTANT: View zone React content is NOT wrapped in observer() due to
 * the React 19 flushSync constraint (see project memory).
 */
export function useMonacoViewZones(
  editor: monacoNs.editor.IStandaloneCodeEditor | null,
  content: string
): ReactPortal[] {
  const managerRef = useRef<ViewZoneManager | null>(null);
  const activeBlocksRef = useRef<Set<string>>(new Set());
  const [portals, setPortals] = useState<ReactPortal[]>([]);

  // Parse PM blocks from content
  const blocks = useMemo(() => parsePMBlockMarkers(content), [content]);

  // Initialize/cleanup manager when editor changes
  useEffect(() => {
    if (!editor) return;

    managerRef.current = new ViewZoneManager(editor);

    return () => {
      managerRef.current?.removeAll();
      managerRef.current = null;
      activeBlocksRef.current.clear();
      setPortals([]);
    };
  }, [editor]);

  // Sync view zones with parsed blocks and build portals
  useEffect(() => {
    const manager = managerRef.current;
    if (!manager || !editor) return;

    const currentBlockIds = new Set(blocks.map((b, i) => `pm-${b.type}-${i}`));
    const previousBlockIds = activeBlocksRef.current;

    // Remove zones that are no longer in the content
    for (const id of previousBlockIds) {
      if (!currentBlockIds.has(id)) {
        manager.removeZone(id);
      }
    }

    // Add new zones
    for (let i = 0; i < blocks.length; i++) {
      const block = blocks[i]!;
      const blockId = `pm-${block.type}-${i}`;

      if (!previousBlockIds.has(blockId)) {
        manager.addZone(blockId, block.endLine, 120);
      }
    }

    // Re-layout existing zones (re-measures heights from DOM)
    manager.relayoutAll();

    activeBlocksRef.current = currentBlockIds;

    // Build portals from the manager's tracked zones
    const newPortals = blocks
      .map((block, i) => {
        const blockId = `pm-${block.type}-${i}`;
        const domNode = manager.getZoneDomNode(blockId);
        if (!domNode) return null;

        return createPortal(
          React.createElement(PMBlockViewZone, {
            type: block.type,
            data: block.data,
            raw: block.raw,
          }),
          domNode,
          blockId
        );
      })
      .filter((p): p is ReactPortal => p !== null);

    // Only update portals if the block set actually changed
    setPortals((prev) => {
      if (
        prev.length === newPortals.length &&
        prev.every((p, idx) => p.key === newPortals[idx]?.key)
      ) {
        return prev;
      }
      return newPortals;
    });
  }, [blocks, editor]);

  return portals;
}
