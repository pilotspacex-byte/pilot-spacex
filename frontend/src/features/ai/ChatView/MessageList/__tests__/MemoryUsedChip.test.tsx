/**
 * Tests for MemoryUsedChip — Phase 69 long-term memory provenance UI.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryUsedChip, type MemorySource } from '../MemoryUsedChip';

const SOURCES: MemorySource[] = [
  { id: 'mem-aaaaaaaa-1111', type: 'note_chunk', score: 0.91 },
  { id: 'mem-bbbbbbbb-2222', type: 'issue', score: 0.78 },
];

describe('MemoryUsedChip', () => {
  it('returns null when sources is undefined', () => {
    const { container } = render(<MemoryUsedChip sources={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when sources is empty', () => {
    const { container } = render(<MemoryUsedChip sources={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders chip when sources are provided', () => {
    render(<MemoryUsedChip sources={SOURCES} />);
    expect(screen.getByTestId('memory-used-chip')).toBeInTheDocument();
    expect(screen.getByText(/2 memories used/i)).toBeInTheDocument();
  });

  it('uses singular noun for one source', () => {
    render(<MemoryUsedChip sources={[SOURCES[0]!]} />);
    expect(screen.getByText(/1 memory used/i)).toBeInTheDocument();
  });

  it('opens popover with source list on click', async () => {
    const user = userEvent.setup();
    render(<MemoryUsedChip sources={SOURCES} />);
    await user.click(screen.getByTestId('memory-used-chip'));
    expect(await screen.findByText('note_chunk')).toBeInTheDocument();
    expect(screen.getByText('issue')).toBeInTheDocument();
    expect(screen.getByText('0.91')).toBeInTheDocument();
    expect(screen.getByText('0.78')).toBeInTheDocument();
  });
});
