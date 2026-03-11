/**
 * ActionButtonBar tests — SKBTN-03
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActionButtonBar } from '../action-button-bar';
import type { SkillActionButton } from '@/services/api/skill-action-buttons';

function makeButton(overrides: Partial<SkillActionButton> = {}): SkillActionButton {
  return {
    id: 'btn-1',
    name: 'Test Button',
    icon: null,
    binding_type: 'skill',
    binding_id: 'skill-1',
    binding_metadata: { skill_name: 'test-skill' },
    sort_order: 0,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('ActionButtonBar', () => {
  it('renders nothing when buttons array is empty', () => {
    const { container } = render(<ActionButtonBar buttons={[]} onButtonClick={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders up to 3 buttons with correct labels', () => {
    const buttons = [
      makeButton({ id: '1', name: 'Button One', sort_order: 0 }),
      makeButton({ id: '2', name: 'Button Two', sort_order: 1 }),
      makeButton({ id: '3', name: 'Button Three', sort_order: 2 }),
    ];

    render(<ActionButtonBar buttons={buttons} onButtonClick={vi.fn()} />);

    expect(screen.getByText('Button One')).toBeInTheDocument();
    expect(screen.getByText('Button Two')).toBeInTheDocument();
    expect(screen.getByText('Button Three')).toBeInTheDocument();
  });

  it('renders "More" dropdown when >3 buttons', () => {
    const buttons = [
      makeButton({ id: '1', name: 'B1', sort_order: 0 }),
      makeButton({ id: '2', name: 'B2', sort_order: 1 }),
      makeButton({ id: '3', name: 'B3', sort_order: 2 }),
      makeButton({ id: '4', name: 'B4', sort_order: 3 }),
    ];

    render(<ActionButtonBar buttons={buttons} onButtonClick={vi.fn()} />);

    // First 3 visible
    expect(screen.getByText('B1')).toBeInTheDocument();
    expect(screen.getByText('B2')).toBeInTheDocument();
    expect(screen.getByText('B3')).toBeInTheDocument();
    // 4th not visible as button text, but More trigger exists
    expect(screen.getByRole('button', { name: /more actions/i })).toBeInTheDocument();
  });

  it('calls onButtonClick with correct button object on click', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    const btn = makeButton({ id: '1', name: 'Click Me' });

    render(<ActionButtonBar buttons={[btn]} onButtonClick={handleClick} />);

    await user.click(screen.getByText('Click Me'));

    expect(handleClick).toHaveBeenCalledWith(btn);
  });

  it('renders icon when button has icon property', () => {
    const btn = makeButton({ icon: 'Zap', name: 'With Icon' });

    render(<ActionButtonBar buttons={[btn]} onButtonClick={vi.fn()} />);

    expect(screen.getByText('With Icon')).toBeInTheDocument();
    // The icon is rendered as an SVG - check the button contains an SVG
    const button = screen.getByText('With Icon').closest('button');
    expect(button?.querySelector('svg')).toBeInTheDocument();
  });

  it('renders disabled state for stale binding', () => {
    const btn = makeButton({
      binding_id: null,
      binding_metadata: {},
      name: 'Stale Button',
    });

    render(<ActionButtonBar buttons={[btn]} onButtonClick={vi.fn()} />);

    const button = screen.getByText('Stale Button').closest('button');
    expect(button).toBeDisabled();
  });
});
