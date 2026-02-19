/**
 * T-123: Unit tests for PresenceIndicator component.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PresenceIndicator } from '../PresenceIndicator';
import type { PeerState } from '../useYjsProvider';

const ALICE: PeerState = { id: 'u1', name: 'Alice Smith', color: '#E74C3C', isAI: false };
const BOB: PeerState = { id: 'u2', name: 'Bob Jones', color: '#3498DB', isAI: false };
const CAROL: PeerState = { id: 'u3', name: 'Carol', color: '#2ECC71', isAI: false };
const HUMANS: PeerState[] = [ALICE, BOB, CAROL];

const AI_PEER: PeerState = { id: 'ai-1', name: 'ExtractIssues', color: '#6B8FAD', isAI: true };

describe('PresenceIndicator', () => {
  it('renders nothing when peers list is empty', () => {
    const { container } = render(<PresenceIndicator peers={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders initials for human peers', () => {
    render(<PresenceIndicator peers={[ALICE]} />);
    // "Alice Smith" -> "AS"
    expect(screen.getByText('AS')).toBeInTheDocument();
  });

  it('renders single initial for single-word name', () => {
    const peer: PeerState = { id: 'x', name: 'Dave', color: '#000', isAI: false };
    render(<PresenceIndicator peers={[peer]} />);
    expect(screen.getByText('DA')).toBeInTheDocument();
  });

  it('excludes currentUserId from the rendered list', () => {
    render(<PresenceIndicator peers={HUMANS} currentUserId="u1" />);
    // u1 (Alice) should be excluded
    expect(screen.queryByText('AS')).not.toBeInTheDocument();
    expect(screen.getByText('BJ')).toBeInTheDocument();
  });

  it('shows overflow badge when peers exceed maxVisible', () => {
    render(<PresenceIndicator peers={HUMANS} maxVisible={2} />);
    // maxVisible=2 with no AI: 2 visible + 1 overflow
    expect(screen.getByText('+1')).toBeInTheDocument();
  });

  it('overflow tooltip lists hidden peer names', () => {
    render(<PresenceIndicator peers={HUMANS} maxVisible={2} />);
    const overflowBadge = screen.getByText('+1');
    expect(overflowBadge.closest('[title]')?.getAttribute('title')).toContain('Carol');
  });

  it('renders bot icon for AI peers', () => {
    render(<PresenceIndicator peers={[AI_PEER]} />);
    expect(screen.getByLabelText(/1 AI skill/)).toBeInTheDocument();
  });

  it('calls onScrollToPeer when human avatar clicked', () => {
    const onScrollToPeer = vi.fn();
    render(<PresenceIndicator peers={[ALICE]} onScrollToPeer={onScrollToPeer} />);
    const btn = screen.getByRole('button', { name: /Alice Smith/ });
    fireEvent.click(btn);
    expect(onScrollToPeer).toHaveBeenCalledWith('u1');
  });

  it('renders ARIA group label with peer names', () => {
    render(<PresenceIndicator peers={[ALICE, BOB]} />);
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', expect.stringContaining('Alice Smith'));
    expect(group).toHaveAttribute('aria-label', expect.stringContaining('Bob Jones'));
  });

  it('shows count badge when multiple AI peers', () => {
    const aiPeers: PeerState[] = [
      AI_PEER,
      { id: 'ai-2', name: 'ImproveWriting', color: '#6B8FAD', isAI: true },
    ];
    render(<PresenceIndicator peers={aiPeers} />);
    // Should show "2" count badge on the AI slot
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
