/**
 * Unit tests for SlashMenu (Phase 87 Plan 02 Wave 2).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { SlashMenu } from '../SlashMenu';
import { SLASH_COMMANDS } from '../extensions/slash-extension';

const noop = () => {};

describe('SlashMenu', () => {
  it('renders all 11 commands when query is empty', () => {
    render(<SlashMenu query="" onSelect={noop} onClose={noop} />);
    for (const cmd of SLASH_COMMANDS) {
      const row = screen.getByTestId(`slash-row-${cmd.id}`);
      expect(row).toBeInTheDocument();
      expect(row).toHaveAttribute('data-slash-row', cmd.id);
    }
  });

  it('filters by substring match on keyword (case-insensitive)', () => {
    render(<SlashMenu query="task" onSelect={noop} onClose={noop} />);
    expect(screen.getByTestId('slash-row-task')).toBeInTheDocument();
    expect(screen.queryByTestId('slash-row-topic')).not.toBeInTheDocument();
    expect(screen.queryByTestId('slash-row-spec')).not.toBeInTheDocument();
  });

  it('filters by substring match on description', () => {
    render(<SlashMenu query="manage" onSelect={noop} onClose={noop} />);
    expect(screen.getByTestId('slash-row-integrations')).toBeInTheDocument();
    expect(screen.queryByTestId('slash-row-task')).not.toBeInTheDocument();
  });

  it('ArrowDown / ArrowUp move aria-selected with wrap-around', () => {
    render(<SlashMenu query="" onSelect={noop} onClose={noop} />);
    const first = screen.getByTestId(`slash-row-${SLASH_COMMANDS[0].id}`);
    const second = screen.getByTestId(`slash-row-${SLASH_COMMANDS[1].id}`);
    const last = screen.getByTestId(`slash-row-${SLASH_COMMANDS[SLASH_COMMANDS.length - 1].id}`);

    expect(first).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(window, { key: 'ArrowDown' });
    expect(second).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(window, { key: 'ArrowUp' });
    expect(first).toHaveAttribute('aria-selected', 'true');

    // Wrap up to last
    fireEvent.keyDown(window, { key: 'ArrowUp' });
    expect(last).toHaveAttribute('aria-selected', 'true');

    // Wrap down to first
    fireEvent.keyDown(window, { key: 'ArrowDown' });
    expect(first).toHaveAttribute('aria-selected', 'true');
  });

  it('Enter calls onSelect with the highlighted command', () => {
    const onSelect = vi.fn();
    render(<SlashMenu query="" onSelect={onSelect} onClose={noop} />);
    fireEvent.keyDown(window, { key: 'ArrowDown' });
    fireEvent.keyDown(window, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].id).toBe(SLASH_COMMANDS[1].id);
  });

  it('Escape calls onClose', () => {
    const onClose = vi.fn();
    render(<SlashMenu query="" onSelect={noop} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders the empty-state literal "No commands match \\"xyz\\"" when filter is empty', () => {
    render(<SlashMenu query="zzznonsense" onSelect={noop} onClose={noop} />);
    expect(screen.getByText('No commands match "zzznonsense"')).toBeInTheDocument();
  });

  it('container exposes data-slash-menu attribute', () => {
    const { container } = render(<SlashMenu query="" onSelect={noop} onClose={noop} />);
    expect(container.querySelector('[data-slash-menu]')).not.toBeNull();
  });
});
