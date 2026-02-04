/**
 * TokenBudgetRing - Unit tests (T025)
 *
 * Covers: SVG rendering, stroke-dasharray percentage mapping,
 * color thresholds, tooltip content, pulse animation, ARIA attributes.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { TokenBudgetRing } from '../token-budget-ring';

const CIRCUMFERENCE = 2 * Math.PI * 10; // ~62.83

describe('TokenBudgetRing', () => {
  it('renders SVG with viewBox and circle elements', () => {
    const { container } = render(<TokenBudgetRing percentage={50} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute('viewBox')).toBe('0 0 24 24');

    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(2);
  });

  it('stroke-dasharray reflects 0% (no fill)', () => {
    const { container } = render(<TokenBudgetRing percentage={0} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    const dasharray = progressCircle?.getAttribute('stroke-dasharray');
    expect(dasharray).toBe(`0 ${CIRCUMFERENCE}`);
  });

  it('stroke-dasharray reflects 50% (half fill)', () => {
    const { container } = render(<TokenBudgetRing percentage={50} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    const dasharray = progressCircle?.getAttribute('stroke-dasharray');
    const expectedFilled = CIRCUMFERENCE * 0.5;
    expect(dasharray).toBe(`${expectedFilled} ${CIRCUMFERENCE}`);
  });

  it('stroke-dasharray reflects 100% (full fill)', () => {
    const { container } = render(<TokenBudgetRing percentage={100} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    const dasharray = progressCircle?.getAttribute('stroke-dasharray');
    expect(dasharray).toBe(`${CIRCUMFERENCE} ${CIRCUMFERENCE}`);
  });

  it('stroke color is green (primary) when < 60%', () => {
    const { container } = render(<TokenBudgetRing percentage={30} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    expect(progressCircle?.getAttribute('stroke')).toBe('var(--primary)');
  });

  it('stroke color is yellow (warning) when 60-79%', () => {
    const { container } = render(<TokenBudgetRing percentage={65} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    expect(progressCircle?.getAttribute('stroke')).toBe('var(--warning)');
  });

  it('stroke color is orange when 80-94%', () => {
    const { container } = render(<TokenBudgetRing percentage={85} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    expect(progressCircle?.getAttribute('stroke')).toBe('#D98040');
  });

  it('stroke color is red (destructive) when >= 95%', () => {
    const { container } = render(<TokenBudgetRing percentage={97} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    expect(progressCircle?.getAttribute('stroke')).toBe('var(--destructive)');
  });

  it('tooltip shows token count on hover', async () => {
    const user = userEvent.setup();
    render(<TokenBudgetRing percentage={42} tokensUsed={3400} tokenBudget={8000} />);

    const trigger = screen.getByRole('progressbar');
    await user.hover(trigger);

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip.textContent).toContain('3.4K / 8K tokens (42%)');
  });

  it('ring pulses when >= 95%', () => {
    const { container } = render(<TokenBudgetRing percentage={96} />);
    const svg = container.querySelector('svg');
    expect(svg?.className.baseVal || svg?.getAttribute('class')).toContain('animate-pulse');
  });

  it('ring does not pulse when < 95%', () => {
    const { container } = render(<TokenBudgetRing percentage={80} />);
    const svg = container.querySelector('svg');
    const classValue = svg?.className.baseVal || svg?.getAttribute('class') || '';
    expect(classValue).not.toContain('animate-pulse');
  });

  it('renders empty ring when percentage is 0', () => {
    const { container } = render(<TokenBudgetRing percentage={0} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    const dasharray = progressCircle?.getAttribute('stroke-dasharray');
    expect(dasharray).toBe(`0 ${CIRCUMFERENCE}`);
  });

  it('has accessible role="progressbar" with aria attributes', () => {
    render(<TokenBudgetRing percentage={42} tokensUsed={3400} tokenBudget={8000} />);

    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toBeTruthy();
    expect(progressbar.getAttribute('aria-valuenow')).toBe('42');
    expect(progressbar.getAttribute('aria-valuemin')).toBe('0');
    expect(progressbar.getAttribute('aria-valuemax')).toBe('100');
    expect(progressbar.getAttribute('aria-label')).toContain('Token budget');
  });

  it('clamps percentage to 0-100 range', () => {
    const { container } = render(<TokenBudgetRing percentage={150} />);
    const progressCircle = container.querySelectorAll('circle')[1];
    const dasharray = progressCircle?.getAttribute('stroke-dasharray');
    // Should clamp to 100%
    expect(dasharray).toBe(`${CIRCUMFERENCE} ${CIRCUMFERENCE}`);
  });

  it('formats tooltip with K suffix correctly', async () => {
    const user = userEvent.setup();
    render(<TokenBudgetRing percentage={10} tokensUsed={800} tokenBudget={8000} />);

    const trigger = screen.getByRole('progressbar');
    await user.hover(trigger);

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip.textContent).toContain('0.8K / 8K tokens (10%)');
  });
});
