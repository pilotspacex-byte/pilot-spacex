/**
 * Unit tests for MentionChip component.
 *
 * Tests rendering for all three entity types, icon selection,
 * data attributes for serialization, aria-label, and onRemove behavior.
 *
 * @module features/ai/ChatView/ChatInput/__tests__/MentionChip
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MentionChip } from '../MentionChip';

describe('MentionChip', () => {
  it('renders Note chip with FileText icon and @title text', () => {
    render(
      <MentionChip entityType="Note" entityId="uuid-note-1" title="My Note" />
    );
    const chip = screen.getByLabelText('Note: My Note');
    expect(chip).toBeDefined();
    expect(chip.getAttribute('data-entity-type')).toBe('Note');
    expect(chip.getAttribute('data-entity-id')).toBe('uuid-note-1');
    expect(chip.textContent).toContain('@My Note');
  });

  it('renders Issue chip with CircleDot icon', () => {
    render(
      <MentionChip entityType="Issue" entityId="uuid-issue-1" title="Bug Fix" />
    );
    const chip = screen.getByLabelText('Issue: Bug Fix');
    expect(chip).toBeDefined();
    expect(chip.getAttribute('data-entity-type')).toBe('Issue');
    expect(chip.getAttribute('data-entity-id')).toBe('uuid-issue-1');
    expect(chip.textContent).toContain('@Bug Fix');
  });

  it('renders Project chip with FolderOpen icon', () => {
    render(
      <MentionChip
        entityType="Project"
        entityId="uuid-proj-1"
        title="Alpha"
      />
    );
    const chip = screen.getByLabelText('Project: Alpha');
    expect(chip).toBeDefined();
    expect(chip.getAttribute('data-entity-type')).toBe('Project');
    expect(chip.getAttribute('data-entity-id')).toBe('uuid-proj-1');
    expect(chip.textContent).toContain('@Alpha');
  });

  it('sets contentEditable to false on the chip span', () => {
    render(
      <MentionChip entityType="Note" entityId="uuid-1" title="Test" />
    );
    const chip = screen.getByLabelText('Note: Test');
    expect(chip.getAttribute('contenteditable')).toBe('false');
  });

  it('does not render remove button when onRemove is not provided', () => {
    render(
      <MentionChip entityType="Note" entityId="uuid-1" title="ReadOnly" />
    );
    expect(screen.queryByLabelText('Remove ReadOnly')).toBeNull();
  });

  it('renders remove button when onRemove is provided', () => {
    const onRemove = vi.fn();
    render(
      <MentionChip
        entityType="Note"
        entityId="uuid-1"
        title="Removable"
        onRemove={onRemove}
      />
    );
    const removeBtn = screen.getByLabelText('Remove Removable');
    expect(removeBtn).toBeDefined();
  });

  it('calls onRemove when remove button is clicked', () => {
    const onRemove = vi.fn();
    render(
      <MentionChip
        entityType="Issue"
        entityId="uuid-2"
        title="ClickMe"
        onRemove={onRemove}
      />
    );
    const removeBtn = screen.getByLabelText('Remove ClickMe');
    fireEvent.click(removeBtn);
    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it('has correct Tailwind classes for styling', () => {
    render(
      <MentionChip entityType="Note" entityId="uuid-1" title="Styled" />
    );
    const chip = screen.getByLabelText('Note: Styled');
    expect(chip.className).toContain('bg-primary/10');
    expect(chip.className).toContain('text-primary');
    expect(chip.className).toContain('inline-flex');
    expect(chip.className).toContain('select-none');
  });

  it('includes removal instruction in aria-label when onRemove is provided', () => {
    const onRemove = vi.fn();
    render(
      <MentionChip entityType="Note" entityId="uuid-1" title="Removable" onRemove={onRemove} />
    );
    const chip = screen.getByLabelText('Note: Removable. Press Backspace to remove.');
    expect(chip).toBeDefined();
  });

  it('omits removal instruction from aria-label when read-only (no onRemove)', () => {
    render(
      <MentionChip entityType="Note" entityId="uuid-1" title="ReadOnly" />
    );
    const chip = screen.getByLabelText('Note: ReadOnly');
    expect(chip.getAttribute('aria-label')).toBe('Note: ReadOnly');
  });
});
