import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DashboardRenderer } from '../renderers/DashboardRenderer';

const defaultProps = {
  data: {} as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'dashboard' as const,
};

describe('DashboardRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render default title when no data provided', () => {
      render(<DashboardRenderer {...defaultProps} />);
      expect(screen.getByDisplayValue('KPI Dashboard')).toBeInTheDocument();
    });

    it('should render custom title from data', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Q1 Metrics' } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByDisplayValue('Q1 Metrics')).toBeInTheDocument();
    });

    it('should render widgets with all properties', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Velocity',
              value: 42,
              trend: 'up',
              unit: 'pts',
              target: 50,
            },
            {
              id: 'w2',
              metric: 'Bug Count',
              value: 15,
              trend: 'down',
              unit: '',
              target: 10,
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByDisplayValue('Velocity')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Bug Count')).toBeInTheDocument();
      expect(screen.getByDisplayValue('42')).toBeInTheDocument();
      expect(screen.getByDisplayValue('15')).toBeInTheDocument();
      expect(screen.getByText('↑ up')).toBeInTheDocument();
      expect(screen.getByText('↓ down')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no widgets', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Dashboard', widgets: [] } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('No widgets yet.')).toBeInTheDocument();
    });

    it('should show empty state when widgets is undefined', () => {
      render(<DashboardRenderer {...defaultProps} />);
      expect(screen.getByText('No widgets yet.')).toBeInTheDocument();
    });
  });

  describe('Title Editing', () => {
    it('should render title as input when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Editable Dashboard' } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      const input = screen.getByDisplayValue('Editable Dashboard');
      expect(input.tagName).toBe('INPUT');
      expect(input).toHaveAttribute('aria-label', 'Dashboard title');
    });

    it('should render title as h3 when readOnly', () => {
      const props = {
        ...defaultProps,
        data: { title: 'Read-Only Dashboard' } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      const heading = screen.getByRole('heading', { level: 3 });
      expect(heading).toHaveTextContent('Read-Only Dashboard');
    });

    it('should call onDataChange when title changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Original' } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const input = screen.getByDisplayValue('Original');
      await user.type(input, 'd');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.title).toBe('Originald');
    });

    it('should not call onDataChange when readOnly', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Read-Only Dashboard' } as Record<string, unknown>,
        readOnly: true,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const heading = screen.getByRole('heading', { level: 3 });
      await user.click(heading);

      expect(onDataChange).not.toHaveBeenCalled();
    });
  });

  describe('Value Formatting', () => {
    it('should format percentage values with % suffix', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Code Coverage',
              value: 85,
              trend: 'flat',
              unit: '%',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should format dollar values with $ prefix', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Revenue',
              value: 50000,
              trend: 'flat',
              unit: '$',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('$50,000')).toBeInTheDocument();
    });

    it('should format generic unit values with unit suffix', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Velocity',
              value: 42,
              trend: 'flat',
              unit: 'pts',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('42 pts')).toBeInTheDocument();
    });

    it('should format values without unit using locale string', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Count',
              value: 1000,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('1,000')).toBeInTheDocument();
    });

    it('should format large numbers with thousands separator', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Budget',
              value: 1500000,
              trend: 'flat',
              unit: '$',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('$1,500,000')).toBeInTheDocument();
    });
  });

  describe('Trend Cycling', () => {
    it('should cycle trend from flat to up when clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: flat/i });
      await user.click(trendButton);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].trend).toBe('up');
    });

    it('should cycle trend from up to down', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'up',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: up/i });
      await user.click(trendButton);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].trend).toBe('down');
    });

    it('should cycle trend from down to flat', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'down',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: down/i });
      await user.click(trendButton);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].trend).toBe('flat');
    });

    it('should not cycle trend when readOnly', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: flat/i });
      expect(trendButton).toBeDisabled();
      await user.click(trendButton);

      expect(onDataChange).not.toHaveBeenCalled();
    });

    it('should display correct arrow for up trend', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'up',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('↑ up')).toBeInTheDocument();
    });

    it('should display correct arrow for down trend', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'down',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('↓ down')).toBeInTheDocument();
    });

    it('should display correct arrow for flat trend', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);
      expect(screen.getByText('→ flat')).toBeInTheDocument();
    });
  });

  describe('Add Widget', () => {
    it('should render add widget button when not readOnly', () => {
      render(<DashboardRenderer {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Add widget' })).toBeInTheDocument();
    });

    it('should not render add widget button when readOnly', () => {
      const props = { ...defaultProps, readOnly: true };
      render(<DashboardRenderer {...props} />);
      expect(screen.queryByRole('button', { name: 'Add widget' })).not.toBeInTheDocument();
    });

    it('should add new widget when button clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Dashboard', widgets: [] } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const addButton = screen.getByRole('button', { name: 'Add widget' });
      await user.click(addButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.widgets).toHaveLength(1);
      expect(call.widgets[0]).toMatchObject({
        metric: '',
        value: 0,
        trend: 'flat',
        unit: '',
      });
      expect(call.widgets[0].id).toMatch(/^w-[a-f0-9-]+$/);
    });

    it('should add widget with unique timestamp-based ID', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: { title: 'Dashboard', widgets: [] } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const addButton = screen.getByRole('button', { name: 'Add widget' });
      await user.click(addButton);
      await user.click(addButton);

      expect(onDataChange).toHaveBeenCalledTimes(2);
      const call1 = onDataChange.mock.calls[0]![0];
      const call2 = onDataChange.mock.calls[1]![0];
      expect(call1.widgets[0].id).not.toBe(call2.widgets[call2.widgets.length - 1].id);
    });
  });

  describe('Remove Widget', () => {
    it('should render remove button for each widget when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric 1',
              value: 100,
              trend: 'flat',
              unit: '',
            },
            {
              id: 'w2',
              metric: 'Metric 2',
              value: 200,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByRole('button', { name: 'Remove Metric 1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Remove Metric 2' })).toBeInTheDocument();
    });

    it('should not render remove buttons when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByRole('button', { name: /Remove/i })).not.toBeInTheDocument();
    });

    it('should remove widget when remove button clicked', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Widget 1',
              value: 100,
              trend: 'flat',
              unit: '',
            },
            {
              id: 'w2',
              metric: 'Widget 2',
              value: 200,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const removeButton = screen.getByRole('button', { name: 'Remove Widget 1' });
      await user.click(removeButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.widgets).toHaveLength(1);
      expect(call.widgets[0].id).toBe('w2');
    });

    it('should handle removing widget with unnamed label', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: '',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const removeButton = screen.getByRole('button', { name: 'Remove widget' });
      await user.click(removeButton);

      expect(onDataChange).toHaveBeenCalledTimes(1);
      const call = onDataChange.mock.calls[0]![0];
      expect(call.widgets).toHaveLength(0);
    });
  });

  describe('Target Display', () => {
    it('should show target input when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: 150,
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByLabelText('Target value')).toBeInTheDocument();
      expect(screen.getByDisplayValue('150')).toBeInTheDocument();
    });

    it('should show target text when readOnly and target exists', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Velocity',
              value: 42,
              trend: 'flat',
              unit: 'pts',
              target: 50,
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByText('Target: 50 pts')).toBeInTheDocument();
    });

    it('should not show target when readOnly and target is null', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: null,
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByText(/Target:/)).not.toBeInTheDocument();
    });

    it('should not show target when readOnly and target is undefined', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByText(/Target:/)).not.toBeInTheDocument();
    });

    it('should format target with percentage unit', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Coverage',
              value: 75,
              trend: 'flat',
              unit: '%',
              target: 90,
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByText('Target: 90%')).toBeInTheDocument();
    });

    it('should format target with dollar unit', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Revenue',
              value: 40000,
              trend: 'flat',
              unit: '$',
              target: 50000,
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByText('Target: $50,000')).toBeInTheDocument();
    });

    it('should update target when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: 150,
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const targetInput = screen.getByLabelText('Target value');
      await user.type(targetInput, '200');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].target).toBeGreaterThan(150);
    });

    it('should clear target when input is emptied', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: 150,
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const targetInput = screen.getByLabelText('Target value');
      await user.clear(targetInput);

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].target).toBeUndefined();
    });
  });

  describe('ReadOnly Mode', () => {
    it('should not render input fields when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByPlaceholderText('Dashboard title')).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Metric name')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Metric value')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Metric unit')).not.toBeInTheDocument();
    });

    it('should display widget data as text when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Velocity',
              value: 42,
              trend: 'up',
              unit: 'pts',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByText('Velocity')).toBeInTheDocument();
      expect(screen.getByText('42 pts')).toBeInTheDocument();
      expect(screen.getByText('↑ up')).toBeInTheDocument();
    });

    it('should not render add/remove buttons when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByRole('button', { name: 'Add widget' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Remove/i })).not.toBeInTheDocument();
    });

    it('should not render target input when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: 150,
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.queryByLabelText('Target value')).not.toBeInTheDocument();
    });

    it('should disable trend button when readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: flat/i });
      expect(trendButton).toBeDisabled();
      expect(trendButton).toHaveAttribute('tabIndex', '-1');
    });

    it('should show unnamed metric placeholder when readOnly and metric is empty', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: '',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        readOnly: true,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByText('Unnamed Metric')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have aria-labels on all input fields', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: 'pts',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByLabelText('Dashboard title')).toBeInTheDocument();
      expect(screen.getByLabelText('Metric name')).toBeInTheDocument();
      expect(screen.getByLabelText('Metric value')).toBeInTheDocument();
      expect(screen.getByLabelText('Metric unit')).toBeInTheDocument();
    });

    it('should have aria-label on trend button with current trend', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'up',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(
        screen.getByRole('button', { name: 'Trend: up. Click to cycle.' })
      ).toBeInTheDocument();
    });

    it('should have aria-label on add widget button', () => {
      render(<DashboardRenderer {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Add widget' })).toBeInTheDocument();
    });

    it('should have aria-label on remove widget button', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Test Widget',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByRole('button', { name: 'Remove Test Widget' })).toBeInTheDocument();
    });

    it('should have aria-label on target input', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
              target: 150,
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      expect(screen.getByLabelText('Target value')).toBeInTheDocument();
    });

    it('should have proper tabIndex on trend button when not readOnly', () => {
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
      };
      render(<DashboardRenderer {...props} />);

      const trendButton = screen.getByRole('button', { name: /Trend: flat/i });
      expect(trendButton).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('Widget Editing', () => {
    it('should update widget metric when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Original',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const input = screen.getByDisplayValue('Original');
      await user.type(input, 'd');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].metric).toBe('Originald');
    });

    it('should update widget value when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: '',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const valueInput = screen.getByDisplayValue('100');
      await user.type(valueInput, '250');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].value).toBeGreaterThan(100);
    });

    it('should update widget unit when input changes', async () => {
      const user = userEvent.setup();
      const onDataChange = vi.fn();
      const props = {
        ...defaultProps,
        data: {
          title: 'Dashboard',
          widgets: [
            {
              id: 'w1',
              metric: 'Metric',
              value: 100,
              trend: 'flat',
              unit: 'pts',
            },
          ],
        } as Record<string, unknown>,
        onDataChange,
      };
      render(<DashboardRenderer {...props} />);

      const unitInput = screen.getByDisplayValue('pts');
      await user.type(unitInput, 's');

      expect(onDataChange).toHaveBeenCalled();
      const lastCall = onDataChange.mock.calls[onDataChange.mock.calls.length - 1]![0];
      expect(lastCall.widgets[0].unit).toBe('ptss');
    });
  });
});
