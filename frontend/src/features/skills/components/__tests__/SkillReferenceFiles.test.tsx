/**
 * SkillReferenceFiles tests — Phase 91 Plan 04, Task 2.
 *
 * Validates the empty state, default-open behaviour for [1..5], default-closed
 * for >5, click dispatch, byte-formatting, and mime-icon dispatch.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { ReferenceFileMeta } from '@/types/skill';
import {
  SkillReferenceFiles,
  __test__,
} from '../SkillReferenceFiles';

function buildRef(over: Partial<ReferenceFileMeta> = {}): ReferenceFileMeta {
  return {
    name: 'architecture.md',
    path: 'architecture.md',
    size_bytes: 2048,
    mime_type: 'text/markdown',
    ...over,
  };
}

describe('SkillReferenceFiles', () => {
  describe('empty state', () => {
    it('renders the verbatim UI-SPEC empty copy', () => {
      render(<SkillReferenceFiles references={[]} onSelect={vi.fn()} />);
      expect(
        screen.getByText('This skill has no reference files.'),
      ).toBeInTheDocument();
    });

    it('does not render the count or trigger when empty', () => {
      render(<SkillReferenceFiles references={[]} onSelect={vi.fn()} />);
      expect(screen.queryByTestId('skill-ref-files-count')).toBeNull();
      expect(screen.queryByTestId('skill-ref-files-trigger')).toBeNull();
    });
  });

  describe('default open behaviour', () => {
    it('defaults open when count is 1', () => {
      const refs = [buildRef({ path: 'a.md' })];
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      expect(screen.getByTestId('skill-ref-files-list')).toBeInTheDocument();
    });

    it('defaults open at the 5-file boundary', () => {
      const refs = Array.from({ length: 5 }).map((_, i) =>
        buildRef({ path: `f${i}.md`, name: `f${i}.md` }),
      );
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      expect(screen.getByTestId('skill-ref-files-list')).toBeInTheDocument();
      expect(screen.getAllByRole('button')).toHaveLength(1 /* trigger */ + 5);
    });

    it('defaults closed when count is > 5', () => {
      const refs = Array.from({ length: 6 }).map((_, i) =>
        buildRef({ path: `f${i}.md`, name: `f${i}.md` }),
      );
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      // Radix CollapsibleContent unmounts (or hides via data-state=closed) when
      // collapsed; either way the list buttons should not be focusable.
      expect(screen.queryByTestId('skill-ref-files-list')).toBeNull();
      // Trigger is still visible with the count.
      expect(screen.getByTestId('skill-ref-files-count')).toHaveTextContent(
        '(6)',
      );
    });

    it('toggles open when the trigger is clicked', () => {
      const refs = Array.from({ length: 6 }).map((_, i) =>
        buildRef({ path: `f${i}.md`, name: `f${i}.md` }),
      );
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      expect(screen.queryByTestId('skill-ref-files-list')).toBeNull();
      fireEvent.click(screen.getByTestId('skill-ref-files-trigger'));
      expect(screen.getByTestId('skill-ref-files-list')).toBeInTheDocument();
    });
  });

  describe('row interaction', () => {
    it('clicking a row calls onSelect with that row\'s path', () => {
      const onSelect = vi.fn();
      const refs = [
        buildRef({ path: 'a.md', name: 'a.md' }),
        buildRef({ path: 'sub/b.py', name: 'b.py', mime_type: 'text/x-python' }),
      ];
      render(<SkillReferenceFiles references={refs} onSelect={onSelect} />);
      fireEvent.click(screen.getByTestId('skill-ref-file-row-sub/b.py'));
      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith('sub/b.py');
    });

    it('renders one button per ref + the trigger button', () => {
      const refs = [
        buildRef({ path: 'a.md' }),
        buildRef({ path: 'b.md', name: 'b.md' }),
        buildRef({ path: 'c.md', name: 'c.md' }),
      ];
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      // 1 trigger + 3 row buttons
      expect(screen.getAllByRole('button')).toHaveLength(4);
    });
  });

  describe('helper: formatBytes', () => {
    const cases: Array<[number, string]> = [
      [0, '0 B'],
      [1, '1 B'],
      [1023, '1023 B'],
      [1024, '1.0 KB'],
      [1024 * 1024, '1.0 MB'],
      [1024 * 1024 * 12.4, '12.4 MB'],
    ];
    it.each(cases)('formats %i bytes as "%s"', (input, expected) => {
      expect(__test__.formatBytes(input)).toBe(expected);
    });
  });

  describe('helper: iconForMime', () => {
    it('returns Image for image/* mimes', () => {
      const Icon = __test__.iconForMime('image/png', 'foo.png');
      expect(Icon.displayName ?? Icon.name).toMatch(/Image/);
    });
    it('returns Code2 for source extensions', () => {
      const Icon = __test__.iconForMime('text/plain', 'foo.py');
      expect(Icon.displayName ?? Icon.name).toMatch(/Code/);
    });
    it('returns Table for csv', () => {
      const Icon = __test__.iconForMime('text/csv', 'data.csv');
      expect(Icon.displayName ?? Icon.name).toMatch(/Table/);
    });
    it('returns FileText for markdown', () => {
      const Icon = __test__.iconForMime('text/markdown', 'doc.md');
      expect(Icon.displayName ?? Icon.name).toMatch(/FileText/);
    });
    it('returns generic File for unknown binary', () => {
      const Icon = __test__.iconForMime(
        'application/octet-stream',
        'mystery.bin',
      );
      expect(Icon.displayName ?? Icon.name).toMatch(/^File$/);
    });
  });

  describe('size pill rendering', () => {
    it('shows the formatted size next to the filename', () => {
      const refs = [buildRef({ path: 'a.md', size_bytes: 1024 })];
      render(<SkillReferenceFiles references={refs} onSelect={vi.fn()} />);
      expect(screen.getByText('1.0 KB')).toBeInTheDocument();
    });
  });
});
