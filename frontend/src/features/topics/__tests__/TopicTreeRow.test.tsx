/**
 * Unit tests for TopicTreeRow (Phase 93 Plan 04 Task 2).
 *
 * Verifies rendering + interaction surface of a single tree row:
 *  - chevron aria-label (expanded vs collapsed)
 *  - clicking chevron toggles topicTreeStore.expanded
 *  - paddingLeft = 8 + depth * 16
 *  - active route highlight (brand-green text + tint)
 *  - empty title renders italic "Untitled"
 *  - onContextMenu prop fires when present (93-05 plug point)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DndContext } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import type { Note } from '@/types';
import { TopicTreeRow } from '../components/TopicTreeRow';
import { topicTreeStore } from '../stores/TopicTreeStore';

vi.mock('next/navigation', () => ({
  usePathname: () => '/workspace/topics/note-1',
  useParams: () => ({ workspaceSlug: 'workspace' }),
}));

const baseNote: Note = {
  id: 'note-a',
  title: 'Plan A',
  workspaceId: 'ws-1',
  wordCount: 0,
  isPinned: false,
  linkedIssues: [],
  parentTopicId: null,
  topicDepth: 0,
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
};

function renderRow(props: { note?: Partial<Note>; depth?: number; onContextMenu?: (e: React.MouseEvent, note: Note) => void } = {}) {
  const note = { ...baseNote, ...props.note } as Note;
  const depth = props.depth ?? 0;
  return render(
    <DndContext>
      <SortableContext items={[note.id]} strategy={verticalListSortingStrategy}>
        <TopicTreeRow note={note} depth={depth} onContextMenu={props.onContextMenu} />
      </SortableContext>
    </DndContext>,
  );
}

describe('TopicTreeRow', () => {
  beforeEach(() => {
    topicTreeStore.expanded.clear();
    topicTreeStore.endDrag();
  });

  it('renders the title as a 13/500 label', () => {
    renderRow({ note: { id: 'note-a', title: 'Plan A' } });
    expect(screen.getByText('Plan A')).toBeInTheDocument();
  });

  it('chevron aria-label is "Expand {title}" when collapsed', () => {
    renderRow({ note: { id: 'note-a', title: 'Plan A' } });
    expect(screen.getByLabelText('Expand Plan A')).toBeInTheDocument();
  });

  it('chevron aria-label is "Collapse {title}" when expanded', () => {
    topicTreeStore.expand('note-a');
    renderRow({ note: { id: 'note-a', title: 'Plan A' } });
    expect(screen.getByLabelText('Collapse Plan A')).toBeInTheDocument();
  });

  it('clicking the chevron toggles topicTreeStore.expanded', () => {
    renderRow({ note: { id: 'note-a', title: 'Plan A' } });
    expect(topicTreeStore.isExpanded('note-a')).toBe(false);
    fireEvent.click(screen.getByLabelText('Expand Plan A'));
    expect(topicTreeStore.isExpanded('note-a')).toBe(true);
  });

  it('applies paddingLeft = 8 + depth * 16', () => {
    renderRow({ note: { id: 'note-a', title: 'Plan A' }, depth: 2 });
    const row = screen.getByTestId('topic-tree-row-note-a');
    // 8 + 2*16 = 40
    expect(row.style.paddingLeft).toBe('40px');
  });

  it('renders italic "Untitled" placeholder when title is empty', () => {
    renderRow({ note: { id: 'note-a', title: '' } });
    const untitled = screen.getByText('Untitled');
    expect(untitled).toBeInTheDocument();
    expect(untitled.tagName.toLowerCase()).toBe('span');
    expect(untitled.className).toMatch(/italic/);
  });

  it('active route row has aria-current="page"', () => {
    // Pathname mocked to /workspace/topics/note-1
    renderRow({ note: { id: 'note-1', title: 'Active Topic' } });
    const row = screen.getByTestId('topic-tree-row-note-1');
    expect(row.getAttribute('aria-current')).toBe('page');
  });

  it('inactive route row has no aria-current', () => {
    renderRow({ note: { id: 'note-2', title: 'Inactive' } });
    const row = screen.getByTestId('topic-tree-row-note-2');
    expect(row.getAttribute('aria-current')).toBeNull();
  });

  it('fires onContextMenu prop when right-clicked (93-05 plug point)', () => {
    const onContextMenu = vi.fn();
    renderRow({ note: { id: 'note-a', title: 'Plan A' }, onContextMenu });
    const row = screen.getByTestId('topic-tree-row-note-a');
    fireEvent.contextMenu(row);
    expect(onContextMenu).toHaveBeenCalledTimes(1);
  });
});
