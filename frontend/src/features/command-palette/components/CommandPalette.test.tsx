import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { File, Pencil, Eye } from 'lucide-react';
import { CommandPalette } from './CommandPalette';
import * as Registry from '../registry/ActionRegistry';
import type { PaletteAction } from '../types';

// cmdk calls scrollIntoView which is not available in jsdom
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock useRecentActions
const mockAddRecent = vi.fn();
const mockGetRecent = vi.fn<() => string[]>().mockReturnValue([]);
vi.mock('../hooks/useRecentActions', () => ({
  useRecentActions: () => ({
    addRecent: mockAddRecent,
    getRecent: mockGetRecent,
  }),
}));

function makeTestActions(): PaletteAction[] {
  return [
    {
      id: 'file:save',
      label: 'Save File',
      category: 'file',
      icon: File,
      shortcut: 'Cmd+S',
      execute: vi.fn(),
      priority: 10,
    },
    {
      id: 'edit:undo',
      label: 'Undo',
      category: 'edit',
      icon: Pencil,
      shortcut: 'Cmd+Z',
      execute: vi.fn(),
      priority: 20,
    },
    {
      id: 'view:preview',
      label: 'Toggle Preview',
      category: 'view',
      icon: Eye,
      execute: vi.fn(),
      priority: 30,
    },
  ];
}

describe('CommandPalette', () => {
  let testActions: PaletteAction[];

  beforeEach(() => {
    testActions = makeTestActions();
    vi.spyOn(Registry, 'getAllActions').mockReturnValue(testActions);
    mockAddRecent.mockClear();
    mockGetRecent.mockReturnValue([]);
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(<CommandPalette isOpen={false} onClose={vi.fn()} />);
    expect(container.querySelector('[role="dialog"]')).toBeNull();
  });

  it('renders Dialog with CommandInput when isOpen is true', () => {
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByPlaceholderText('Type a command...')).toBeInTheDocument();
  });

  it('shows all actions when query is empty and no recent actions', () => {
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText('Save File')).toBeInTheDocument();
    expect(screen.getByText('Undo')).toBeInTheDocument();
    expect(screen.getByText('Toggle Preview')).toBeInTheDocument();
  });

  it('filters actions by query: typing "save" shows only matching actions', async () => {
    const user = userEvent.setup();
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText('Type a command...');
    await user.type(input, 'save');

    expect(screen.getByText('Save File')).toBeInTheDocument();
    expect(screen.queryByText('Undo')).toBeNull();
    expect(screen.queryByText('Toggle Preview')).toBeNull();
  });

  it('executes action on select and closes palette', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<CommandPalette isOpen={true} onClose={onClose} />);

    await user.click(screen.getByText('Save File'));

    expect(testActions[0]!.execute).toHaveBeenCalled();
    expect(mockAddRecent).toHaveBeenCalledWith('file:save');
    expect(onClose).toHaveBeenCalled();
  });

  it('shows recently used actions when query is empty', () => {
    mockGetRecent.mockReturnValue(['edit:undo']);
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);

    // Should have a "Recently Used" heading
    expect(screen.getByText('Recently Used')).toBeInTheDocument();
  });

  it('shows empty state when query matches nothing', async () => {
    const user = userEvent.setup();
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText('Type a command...');
    await user.type(input, 'zzzznonexistent');

    expect(screen.getByText('No matching actions')).toBeInTheDocument();
  });

  it('displays keyboard shortcuts for actions that have them', () => {
    render(<CommandPalette isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText('Cmd+S')).toBeInTheDocument();
    expect(screen.getByText('Cmd+Z')).toBeInTheDocument();
  });
});
