import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TimelineRenderer } from '../renderers/TimelineRenderer';

const defaultProps = {
  data: {} as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'timeline' as const,
};

describe('TimelineRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render default title when no data provided', () => {
      render(<TimelineRenderer {...defaultProps} />);
      expect(screen.getByDisplayValue('Project Timeline')).toBeInTheDocument();
    });

    it('should render custom title from data', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Q1 Roadmap' } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);
      expect(screen.getByDisplayValue('Q1 Roadmap')).toBeInTheDocument();
    });

    it('should render milestones with all properties', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Project Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Alpha Release',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'Beta Release',
              date: '2026-04-01',
              status: 'at-risk',
              dependencies: ['m1'],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByDisplayValue('Alpha Release')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Beta Release')).toBeInTheDocument();
      expect(screen.getByDisplayValue('2026-03-01')).toBeInTheDocument();
      expect(screen.getByDisplayValue('2026-04-01')).toBeInTheDocument();
      expect(screen.getByText('On Track')).toBeInTheDocument();
      expect(screen.getByText('At Risk')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no milestones', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Timeline', milestones: [] } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);
      expect(screen.getByText('No milestones yet.')).toBeInTheDocument();
    });

    it('should show empty state when milestones is undefined', () => {
      render(<TimelineRenderer {...defaultProps} />);
      expect(screen.getByText('No milestones yet.')).toBeInTheDocument();
    });
  });

  describe('Title Editing', () => {
    it('should render title as input when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Editable Title' } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);
      const input = screen.getByDisplayValue('Editable Title');
      expect(input.tagName).toBe('INPUT');
      expect(input).toHaveAttribute('aria-label', 'Timeline title');
    });

    it('should render title as h3 when readOnly', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Read-Only Title' } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);
      const heading = screen.getByRole('heading', { level: 3 });
      expect(heading).toHaveTextContent('Read-Only Title');
    });

    it('should call onDataChange when title changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Original' } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const input = screen.getByDisplayValue('Original');
      await user.type(input, 'd');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.title).toBe('Originald');
    });

    it('should not call onDataChange when readOnly and title clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Read-Only Title' } as Record<string, unknown>,
        readOnly: true,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const heading = screen.getByRole('heading', { level: 3 });
      await user.click(heading);

      expect(onDataChange).not.toHaveBeenCalled();
    });
  });

  describe('Status Cycling', () => {
    it('should cycle status from on-track to at-risk when clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone 1.*On Track/i });
      await user.click(milestone);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].status).toBe('at-risk');
    });

    it('should cycle status from at-risk to blocked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'at-risk',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone 1.*At Risk/i });
      await user.click(milestone);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].status).toBe('blocked');
    });

    it('should cycle status from blocked to on-track', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'blocked',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone 1.*Blocked/i });
      await user.click(milestone);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].status).toBe('on-track');
    });

    it('should cycle status when Enter key pressed', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone 1.*On Track/i });
      milestone.focus();
      await user.keyboard('{Enter}');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].status).toBe('at-risk');
    });

    it('should not cycle status when readOnly', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone 1.*On Track/i });
      await user.click(milestone);

      expect(onDataChange).not.toHaveBeenCalled();
    });
  });

  describe('Add Milestone', () => {
    it('should render add milestone button when not readOnly', () => {
      render(<TimelineRenderer {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Add milestone' })).toBeInTheDocument();
    });

    it('should not render add milestone button when readOnly', () => {
      const props = { ...defaultProps, readOnly: true };
      render(<TimelineRenderer {...props} />);
      expect(screen.queryByRole('button', { name: 'Add milestone' })).not.toBeInTheDocument();
    });

    it('should add new milestone when button clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Timeline', milestones: [] } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const addButton = screen.getByRole('button', { name: 'Add milestone' });
      await user.click(addButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.milestones).toHaveLength(1);
      expect(call.milestones[0]).toMatchObject({
        name: '',
        date: '',
        status: 'on-track',
        dependencies: [],
      });
      expect(call.milestones[0].id).toMatch(/^m-[a-f0-9-]+$/);
    });

    it('should add milestone with unique timestamp-based ID', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Timeline', milestones: [] } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const addButton = screen.getByRole('button', { name: 'Add milestone' });
      await user.click(addButton);
      await user.click(addButton);

      expect(onDataChange).toHaveBeenCalledTimes(2);
      const call1 = onDataChange.mock.calls[0]![0];
      const call2 = onDataChange.mock.calls[1]![0];
      expect(call1.milestones[0].id).not.toBe(call2.milestones[call2.milestones.length - 1].id);
    });
  });

  describe('Remove Milestone', () => {
    it('should render remove button for each milestone when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'Milestone 2',
              date: '2026-04-01',
              status: 'at-risk',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByRole('button', { name: 'Remove Milestone 1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Remove Milestone 2' })).toBeInTheDocument();
    });

    it('should not render remove buttons when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.queryByRole('button', { name: /Remove/i })).not.toBeInTheDocument();
    });

    it('should remove milestone when remove button clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'Milestone 2',
              date: '2026-04-01',
              status: 'at-risk',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const removeButton = screen.getByRole('button', { name: 'Remove Milestone 1' });
      await user.click(removeButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.milestones).toHaveLength(1);
      expect(call.milestones[0].id).toBe('m2');
    });

    it('should handle removing milestone with unnamed label', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: '',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const removeButton = screen.getByRole('button', { name: 'Remove milestone' });
      await user.click(removeButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.milestones).toHaveLength(0);
    });
  });

  describe('Date Sorting', () => {
    it('should sort milestones by date ascending', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm3',
              name: 'Third',
              date: '2026-06-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm1',
              name: 'First',
              date: '2026-02-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'Second',
              date: '2026-04-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestoneNames = screen.getAllByPlaceholderText('Milestone name');
      expect(milestoneNames[0]).toHaveValue('First');
      expect(milestoneNames[1]).toHaveValue('Second');
      expect(milestoneNames[2]).toHaveValue('Third');
    });

    it('should place milestones without dates at the end', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm2',
              name: 'No Date',
              date: '',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm1',
              name: 'With Date',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestoneNames = screen.getAllByPlaceholderText('Milestone name');
      expect(milestoneNames[0]).toHaveValue('With Date');
      expect(milestoneNames[1]).toHaveValue('No Date');
    });

    it('should preserve order when all milestones have no dates', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'First',
              date: '',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'Second',
              date: '',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestoneNames = screen.getAllByPlaceholderText('Milestone name');
      expect(milestoneNames[0]).toHaveValue('First');
      expect(milestoneNames[1]).toHaveValue('Second');
    });
  });

  describe('ReadOnly Mode', () => {
    it('should not render input fields when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.queryByPlaceholderText('Timeline title')).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Milestone name')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Milestone date')).not.toBeInTheDocument();
    });

    it('should display milestone data as text when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Alpha Release',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByText('Alpha Release')).toBeInTheDocument();
      expect(screen.getByText('2026-03-01')).toBeInTheDocument();
      expect(screen.getByText('On Track')).toBeInTheDocument();
    });

    it('should show dash for empty date when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'No Date Milestone',
              date: '',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByText('—')).toBeInTheDocument();
    });

    it('should not render add/remove buttons when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.queryByRole('button', { name: 'Add milestone' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Remove/i })).not.toBeInTheDocument();
    });
  });

  describe('Summary Footer', () => {
    it('should display correct counts for each status', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'M1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm2',
              name: 'M2',
              date: '2026-04-01',
              status: 'on-track',
              dependencies: [],
            },
            {
              id: 'm3',
              name: 'M3',
              date: '2026-05-01',
              status: 'at-risk',
              dependencies: [],
            },
            {
              id: 'm4',
              name: 'M4',
              date: '2026-06-01',
              status: 'blocked',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByText('2 on track')).toBeInTheDocument();
      expect(screen.getByText('1 at risk')).toBeInTheDocument();
      expect(screen.getByText('1 blocked')).toBeInTheDocument();
    });

    it('should show zero counts when no milestones have that status', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'M1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByText('1 on track')).toBeInTheDocument();
      expect(screen.getByText('0 at risk')).toBeInTheDocument();
      expect(screen.getByText('0 blocked')).toBeInTheDocument();
    });

    it('should not render summary when no milestones', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Timeline', milestones: [] } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.queryByText(/on track/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/at risk/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/blocked/i)).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label on milestone with name and status', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Release',
              date: '2026-03-01',
              status: 'at-risk',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: 'Release: At Risk' });
      expect(milestone).toBeInTheDocument();
    });

    it('should have aria-label on unnamed milestone', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: '',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: 'Unnamed: On Track' });
      expect(milestone).toBeInTheDocument();
    });

    it('should have aria-labels on all input fields', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone 1',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByLabelText('Timeline title')).toBeInTheDocument();
      expect(screen.getByLabelText('Milestone name')).toBeInTheDocument();
      expect(screen.getByLabelText('Milestone date')).toBeInTheDocument();
    });

    it('should have aria-label on add milestone button', () => {
      render(<TimelineRenderer {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Add milestone' })).toBeInTheDocument();
    });

    it('should have aria-label on remove milestone button', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Test Milestone',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      expect(screen.getByRole('button', { name: 'Remove Test Milestone' })).toBeInTheDocument();
    });

    it('should have proper tabIndex for readOnly mode', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone.*On Track/i });
      expect(milestone).toHaveAttribute('tabIndex', '-1');
    });

    it('should have proper tabIndex for editable mode', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
      };
      render(<TimelineRenderer {...props} />);

      const milestone = screen.getByRole('button', { name: /Milestone.*On Track/i });
      expect(milestone).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('Milestone Editing', () => {
    it('should update milestone name when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Original',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const input = screen.getByDisplayValue('Original');
      await user.type(input, 'd');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].name).toBe('Originald');
    });

    it('should update milestone date when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone',
              date: '',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const dateInput = screen.getByLabelText('Milestone date');
      await user.type(dateInput, '2026-05-15');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.milestones[0].date).toBe('2026-05-15');
    });

    it('should stop propagation when clicking input fields', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Timeline',
          milestones: [
            {
              id: 'm1',
              name: 'Milestone',
              date: '2026-03-01',
              status: 'on-track',
              dependencies: [],
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<TimelineRenderer {...props} />);

      const nameInput = screen.getByDisplayValue('Milestone');
      await user.click(nameInput);

      const statusChangeCalls = onDataChange.mock.calls.filter(
        (call) => call[0].milestones[0].status !== 'on-track'
      );
      expect(statusChangeCalls).toHaveLength(0);
    });
  });
});
