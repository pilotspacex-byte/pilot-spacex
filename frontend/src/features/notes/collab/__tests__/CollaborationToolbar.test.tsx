/**
 * T-120: Unit tests for CollaborationToolbar component.
 *
 * Tests:
 * - Returns null when online and no visible peers
 * - Shows ConnectionStatus when offline/error even with no peers
 * - Shows PresenceIndicator when peers present
 * - Shows "N editing" label for human peers
 * - Does not show label for AI-only peers
 * - Accessible: role="group" with aria-label summarising collaborators
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollaborationToolbar } from '../CollaborationToolbar';
import type { PeerState } from '../useYjsProvider';

const ALICE: PeerState = { id: 'u1', name: 'Alice', color: '#E74C3C', isAI: false };
const BOB: PeerState = { id: 'u2', name: 'Bob', color: '#3498DB', isAI: false };
const AI_PEER: PeerState = { id: 'ai-1', name: 'PilotAgent', color: '#6B8FAD', isAI: true };

describe('CollaborationToolbar — visibility', () => {
  it('returns null when online and no peers', () => {
    const { container } = render(<CollaborationToolbar peers={[]} connectionStatus="online" />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when online and all peers are currentUser', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} currentUserId="u1" connectionStatus="online" />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders when offline even with no peers', () => {
    const { container } = render(<CollaborationToolbar peers={[]} connectionStatus="offline" />);
    expect(container.firstChild).not.toBeNull();
  });

  it('renders when error even with no peers', () => {
    const { container } = render(<CollaborationToolbar peers={[]} connectionStatus="error" />);
    expect(container.firstChild).not.toBeNull();
  });

  it('renders when syncing even with no peers', () => {
    const { container } = render(<CollaborationToolbar peers={[]} connectionStatus="syncing" />);
    expect(container.firstChild).not.toBeNull();
  });

  it('renders when online with peers present', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} connectionStatus="online" />
    );
    expect(container.firstChild).not.toBeNull();
  });
});

describe('CollaborationToolbar — editing label', () => {
  it('shows "1 editing" for 1 human peer', () => {
    render(<CollaborationToolbar peers={[ALICE]} connectionStatus="online" />);
    expect(screen.getByText('1 editing')).toBeInTheDocument();
  });

  it('shows "2 editing" for 2 human peers', () => {
    render(<CollaborationToolbar peers={[ALICE, BOB]} connectionStatus="online" />);
    expect(screen.getByText('2 editing')).toBeInTheDocument();
  });

  it('does not show editing label for AI-only peers', () => {
    render(<CollaborationToolbar peers={[AI_PEER]} connectionStatus="online" />);
    expect(screen.queryByText(/editing/)).toBeNull();
  });

  it('counts only human peers when AI peers also present', () => {
    render(<CollaborationToolbar peers={[ALICE, AI_PEER]} connectionStatus="online" />);
    expect(screen.getByText('1 editing')).toBeInTheDocument();
  });

  it('does not show editing label when no human peers and offline', () => {
    render(<CollaborationToolbar peers={[]} connectionStatus="offline" />);
    expect(screen.queryByText(/editing/)).toBeNull();
  });
});

describe('CollaborationToolbar — accessibility', () => {
  it('has role="group"', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} connectionStatus="online" />
    );
    expect(container.querySelector('[role="group"]')).not.toBeNull();
  });

  it('aria-label mentions collaborator count when peers present', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} connectionStatus="online" />
    );
    const group = container.querySelector('[role="group"]');
    expect(group?.getAttribute('aria-label')).toMatch(/1 collaborator/);
  });

  it('aria-label is plural for multiple collaborators', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE, BOB]} connectionStatus="online" />
    );
    const group = container.querySelector('[role="group"]');
    expect(group?.getAttribute('aria-label')).toMatch(/2 collaborators/);
  });

  it('aria-label is "Collaboration status" when no human peers', () => {
    const { container } = render(
      <CollaborationToolbar peers={[AI_PEER]} connectionStatus="online" />
    );
    const group = container.querySelector('[role="group"]');
    expect(group?.getAttribute('aria-label')).toBe('Collaboration status');
  });

  it('editing label has aria-hidden="true"', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} connectionStatus="online" />
    );
    // Find the span that contains '1 editing' (multiple aria-hidden elements may exist)
    const ariaHiddenEls = container.querySelectorAll('[aria-hidden="true"]');
    const editingLabel = Array.from(ariaHiddenEls).find((el) => el.textContent === '1 editing');
    expect(editingLabel).not.toBeUndefined();
  });
});

describe('CollaborationToolbar — className prop', () => {
  it('applies custom className to root element', () => {
    const { container } = render(
      <CollaborationToolbar peers={[ALICE]} connectionStatus="online" className="my-custom-class" />
    );
    expect(container.querySelector('.my-custom-class')).not.toBeNull();
  });
});

describe('CollaborationToolbar — maxVisible', () => {
  it('passes maxVisible to PresenceIndicator', () => {
    // With 3 peers and maxVisible=2, overflow badge should appear
    const peers: PeerState[] = [
      { id: 'u1', name: 'Alice', color: '#aaa', isAI: false },
      { id: 'u2', name: 'Bob', color: '#bbb', isAI: false },
      { id: 'u3', name: 'Carol', color: '#ccc', isAI: false },
    ];
    render(<CollaborationToolbar peers={peers} connectionStatus="online" maxVisible={2} />);
    expect(screen.getByText('+1')).toBeInTheDocument();
  });
});
