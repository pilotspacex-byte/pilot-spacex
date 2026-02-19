/**
 * PMBlockExtension — Generic TipTap node for PM block types.
 *
 * Serves as the single container node for: decision, form, raci,
 * risk, timeline, dashboard. Rendering is delegated to type-specific
 * renderers via PMBlockNodeView.
 *
 * Attrs:
 * - blockType: one of PM_BLOCK_TYPES
 * - data: JSON string containing type-specific data
 * - version: schema version for forward-compat migrations
 *
 * Content transport: JSON via TipTap insertContentAt() (RD-008).
 * NOT markdown — complex PM structures have no markdown representation.
 *
 * @module pm-blocks/PMBlockExtension
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { Fragment, Slice, type Node as ProseMirrorNode } from '@tiptap/pm/model';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { PMBlockNodeView } from './PMBlockNodeView';

/** All supported PM block types. */
export const PM_BLOCK_TYPES = [
  // Original 6
  'decision',
  'form',
  'raci',
  'risk',
  'timeline',
  'dashboard',
  // Feature 017 — PM Block Engine (T-228)
  'sprint-board',
  'dependency-map',
  'capacity-plan',
  'release-notes',
] as const;

export type PMBlockType = (typeof PM_BLOCK_TYPES)[number];

export interface PMBlockAttrs {
  blockType: PMBlockType;
  data: string;
  version: number;
}

/**
 * Clean PM block data on paste (FR-054).
 * Removes user-specific and state-dependent fields so pasted blocks
 * start fresh: decisions revert to 'open', forms clear responses,
 * risks clear owners.
 */
function cleanPMBlockData(blockType: string, rawData: string): string {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(rawData);
  } catch {
    return rawData;
  }

  if (blockType === 'decision') {
    data = { ...data, status: 'open', decidedDate: undefined, issueId: undefined };
  } else if (blockType === 'form') {
    data = { ...data, responses: [] };
  } else if (blockType === 'risk') {
    const risks = Array.isArray(data.risks)
      ? (data.risks as Record<string, unknown>[]).map((r) => ({ ...r, owner: undefined }))
      : data.risks;
    data = { ...data, risks };
  }

  return JSON.stringify(data);
}

/** Recursively map over a Fragment, transforming nodes. */
function mapFragment(fragment: Fragment, fn: (node: ProseMirrorNode) => ProseMirrorNode): Fragment {
  const nodes: ProseMirrorNode[] = [];
  fragment.forEach((node) => {
    const mapped = fn(node);
    if (mapped.content.childCount > 0) {
      nodes.push(mapped.copy(mapFragment(mapped.content, fn)));
    } else {
      nodes.push(mapped);
    }
  });
  return Fragment.from(nodes);
}

/** Serialize PM block data to human-readable text for clipboard export (FR-055). */
function serializePMBlockToText(blockType: string, rawData: string): string {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(rawData);
  } catch {
    return `[${blockType}]`;
  }

  const title = (data.title as string) || blockType;
  const lines: string[] = [`[${blockType.toUpperCase()}] ${title}`];

  if (blockType === 'decision') {
    lines.push(`Status: ${(data.status as string) || 'open'}`);
    const options = data.options as Array<Record<string, unknown>> | undefined;
    options?.forEach((opt) => lines.push(`- ${opt.label as string}`));
  } else if (blockType === 'risk') {
    const risks = data.risks as Array<Record<string, unknown>> | undefined;
    risks?.forEach((r) => {
      const score = ((r.probability as number) || 0) * ((r.impact as number) || 0);
      lines.push(`- ${r.description as string} (Score: ${score})`);
    });
  } else if (blockType === 'timeline') {
    const milestones = data.milestones as Array<Record<string, unknown>> | undefined;
    milestones?.forEach((m) =>
      lines.push(
        `- ${m.name as string} [${m.status as string}] ${m.date ? `(${m.date as string})` : ''}`
      )
    );
  } else if (blockType === 'dashboard') {
    const widgets = data.widgets as Array<Record<string, unknown>> | undefined;
    widgets?.forEach((w) =>
      lines.push(
        `- ${w.metric as string}: ${w.value as number}${w.unit ? ` ${w.unit as string}` : ''}`
      )
    );
  }

  return lines.join('\n');
}

export const PMBlockExtension = Node.create({
  name: 'pmBlock',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      blockType: {
        default: 'decision' as PMBlockType,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-block-type') || 'decision',
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-block-type': attributes.blockType as string,
        }),
      },
      data: {
        default: '{}',
        parseHTML: (element: HTMLElement) => element.getAttribute('data-pm-data') || '{}',
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-pm-data': attributes.data as string,
        }),
      },
      version: {
        default: 1,
        parseHTML: (element: HTMLElement) => {
          const val = element.getAttribute('data-version');
          return val ? parseInt(val, 10) : 1;
        },
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-version': String(attributes.version),
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-block-type]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { class: 'pm-block' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(PMBlockNodeView);
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('pmBlockPasteCleanup'),
        props: {
          /** Export PM blocks as structured text on copy (FR-055). */
          clipboardTextSerializer: (slice) => {
            const parts: string[] = [];
            slice.content.forEach((node) => {
              if (node.type.name === 'pmBlock') {
                parts.push(
                  serializePMBlockToText(
                    node.attrs.blockType as string,
                    (node.attrs.data as string) || '{}'
                  )
                );
              }
            });
            return parts.length > 0 ? parts.join('\n\n') : '';
          },
          /** Clean PM block data on paste (FR-054). */
          transformPasted(slice) {
            const cleaned = mapFragment(slice.content, (node) => {
              if (node.type.name !== 'pmBlock') return node;

              const blockType = node.attrs.blockType as string;
              const rawData = (node.attrs.data as string) || '{}';
              const cleanedData = cleanPMBlockData(blockType, rawData);

              return node.type.create(
                { ...node.attrs, data: cleanedData },
                node.content,
                node.marks
              );
            });

            return new Slice(cleaned, slice.openStart, slice.openEnd);
          },
        },
      }),
    ];
  },
});
