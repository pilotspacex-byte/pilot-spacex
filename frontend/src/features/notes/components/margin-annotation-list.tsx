/**
 * Margin Annotation List - Displays annotations positioned by block
 * T168: Renders annotations in margin with absolute positioning
 *
 * Features:
 * - Block position synchronization
 * - Annotation grouping per block
 * - Click handling for selection
 * - Empty state
 */
'use client';

import { observer } from 'mobx-react-lite';
import { useStores } from '@/stores/RootStore';
import { AnnotationCard } from './annotation-card';
import type { BlockPosition } from '@/components/editor/plugins/annotation-positioning';

interface MarginAnnotationListProps {
  noteId: string;
  blockPositions: BlockPosition[];
}

export const MarginAnnotationList = observer(function MarginAnnotationList({
  noteId,
  blockPositions,
}: MarginAnnotationListProps) {
  const { ai } = useStores();
  const { marginAnnotation } = ai;

  const annotationsByBlock = marginAnnotation.getAnnotationsByBlock(noteId);

  if (annotationsByBlock.size === 0) {
    return null;
  }

  return (
    <div
      className="margin-annotation-list relative h-full"
      role="complementary"
      aria-label="Annotations"
    >
      {blockPositions.map((block) => {
        const annotations = annotationsByBlock.get(block.blockId) || [];
        if (annotations.length === 0) return null;

        return (
          <div
            key={block.blockId}
            className="absolute right-0 w-full px-2"
            style={{
              top: `${block.top}px`,
              minHeight: `${block.height}px`,
            }}
          >
            {annotations.map((annotation) => (
              <AnnotationCard
                key={annotation.id}
                annotation={annotation}
                isSelected={marginAnnotation.selectedAnnotationId === annotation.id}
                onSelect={() => marginAnnotation.selectAnnotation(annotation.id)}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
});
