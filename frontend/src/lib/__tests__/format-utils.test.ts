import { describe, it, expect, vi, afterEach } from 'vitest';
import { abbreviatedTimeAgo, safeFormatDistance } from '../format-utils';

describe('abbreviatedTimeAgo', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty string for null input', () => {
    expect(abbreviatedTimeAgo(null)).toBe('');
  });

  it('returns empty string for undefined input', () => {
    expect(abbreviatedTimeAgo(undefined)).toBe('');
  });

  it('returns empty string for invalid date string', () => {
    expect(abbreviatedTimeAgo('not-a-date')).toBe('');
  });

  it('returns "now" for less than 1 minute ago', () => {
    const tenSecsAgo = new Date(Date.now() - 10_000).toISOString();
    expect(abbreviatedTimeAgo(tenSecsAgo)).toBe('now');
  });

  it('returns minutes for less than 1 hour ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-20T12:00:00Z'));

    const thirtyMinAgo = new Date('2026-02-20T11:30:00Z').toISOString();
    expect(abbreviatedTimeAgo(thirtyMinAgo)).toBe('30m');

    const oneMinAgo = new Date('2026-02-20T11:59:00Z').toISOString();
    expect(abbreviatedTimeAgo(oneMinAgo)).toBe('1m');

    // Boundary: exactly 59 minutes
    const fiftyNineMin = new Date('2026-02-20T11:01:00Z').toISOString();
    expect(abbreviatedTimeAgo(fiftyNineMin)).toBe('59m');
  });

  it('returns hours for less than 24 hours ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-20T12:00:00Z'));

    const twoHoursAgo = new Date('2026-02-20T10:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(twoHoursAgo)).toBe('2h');

    // Boundary: exactly 1 hour
    const oneHour = new Date('2026-02-20T11:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(oneHour)).toBe('1h');

    // Boundary: 23 hours
    const twentyThreeH = new Date('2026-02-19T13:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(twentyThreeH)).toBe('23h');
  });

  it('returns days for less than 7 days ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-20T12:00:00Z'));

    const threeDaysAgo = new Date('2026-02-17T12:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(threeDaysAgo)).toBe('3d');

    // Boundary: exactly 1 day
    const oneDay = new Date('2026-02-19T12:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(oneDay)).toBe('1d');
  });

  it('returns weeks for 7+ days ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-20T12:00:00Z'));

    const twoWeeksAgo = new Date('2026-02-06T12:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(twoWeeksAgo)).toBe('2w');

    // Boundary: exactly 7 days
    const oneWeek = new Date('2026-02-13T12:00:00Z').toISOString();
    expect(abbreviatedTimeAgo(oneWeek)).toBe('1w');
  });

  it('returns "now" for future dates (clock skew guard)', () => {
    const futureDate = new Date(Date.now() + 60_000).toISOString();
    expect(abbreviatedTimeAgo(futureDate)).toBe('now');
  });
});

describe('safeFormatDistance', () => {
  it('returns "recently" for null', () => {
    expect(safeFormatDistance(null)).toBe('recently');
  });

  it('returns "recently" for undefined', () => {
    expect(safeFormatDistance(undefined)).toBe('recently');
  });

  it('returns "recently" for invalid date', () => {
    expect(safeFormatDistance('garbage')).toBe('recently');
  });

  it('returns relative distance for valid date', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60_000).toISOString();
    const result = safeFormatDistance(fiveMinAgo);
    expect(result).toContain('ago');
  });
});
