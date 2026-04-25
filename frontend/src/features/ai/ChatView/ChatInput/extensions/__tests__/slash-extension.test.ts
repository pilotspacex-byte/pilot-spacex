/**
 * Tests for slash-extension — pure helpers + registry shape.
 * Phase 87 Plan 02 (Wave 2). The slash trigger lives in ChatInput's plain
 * contenteditable handler (not TipTap Suggestion) — see SUMMARY deviations.
 */
import { describe, expect, it } from 'vitest';
import { SLASH_COMMANDS, filterCommands, shouldTrigger } from '../slash-extension';

describe('shouldTrigger', () => {
  it('returns true when text-before-cursor is just "/" and is at start of input', () => {
    expect(shouldTrigger({ textBeforeCursor: '/' })).toBe(true);
  });

  it('returns true when "/" is followed by query chars at start of input (no whitespace)', () => {
    expect(shouldTrigger({ textBeforeCursor: '/top' })).toBe(true);
  });

  it('returns false when "/" appears mid-word (e.g. "http://")', () => {
    expect(shouldTrigger({ textBeforeCursor: 'http://' })).toBe(false);
  });

  it('returns false when paragraph contains other text before the "/"', () => {
    expect(shouldTrigger({ textBeforeCursor: 'hello /' })).toBe(false);
  });

  it('returns false on empty input', () => {
    expect(shouldTrigger({ textBeforeCursor: '' })).toBe(false);
  });
});

describe('filterCommands', () => {
  it('returns the full registry in order when query is empty', () => {
    const result = filterCommands('');
    expect(result).toHaveLength(SLASH_COMMANDS.length);
    expect(result.map((c) => c.id)).toEqual(SLASH_COMMANDS.map((c) => c.id));
  });

  it('matches against keyword (substring, case-insensitive)', () => {
    const result = filterCommands('TASK');
    expect(result.some((c) => c.id === 'task')).toBe(true);
  });

  it('matches against description (substring, case-insensitive)', () => {
    // "Manage integrations" matches "manage"
    const result = filterCommands('manage');
    expect(result.some((c) => c.id === 'integrations')).toBe(true);
  });

  it('returns empty array when no command matches', () => {
    expect(filterCommands('xyzqqq')).toEqual([]);
  });
});

describe('SLASH_COMMANDS registry', () => {
  // Phase 91 Plan 05: /skills was added BEFORE /skill (typing "/sk" should
  // surface the gallery option first), bumping the registry from 11 to 12
  // entries. /skill was repurposed: description "Open a skill by name" and
  // stubTolerant removed (the route is no longer a stub).
  // Phase 92 Plan 03: /skills-graph inserted between /skills and /skill so
  // typing "/sk" surfaces them in the order skills, skills-graph, skill.
  // Registry size bumped from 12 to 13.
  it('contains exactly 13 entries in the documented order', () => {
    expect(SLASH_COMMANDS).toHaveLength(13);
    expect(SLASH_COMMANDS.map((c) => c.id)).toEqual([
      'topic',
      'task',
      'spec',
      'decision',
      'skills',
      'skills-graph',
      'skill',
      'members',
      'settings',
      'integrations',
      'kg',
      'standup',
      'digest',
    ]);
  });

  it('every command exposes keyword starting with "/"', () => {
    for (const cmd of SLASH_COMMANDS) {
      expect(cmd.keyword.startsWith('/')).toBe(true);
    }
  });

  it('routing/picker commands provide a routeTemplate; invoke commands provide an invoke', () => {
    for (const cmd of SLASH_COMMANDS) {
      if (cmd.kind === 'invoke') {
        expect(typeof cmd.invoke).toBe('function');
      } else {
        expect(typeof cmd.routeTemplate).toBe('function');
      }
    }
  });
});

describe('Phase 91 Plan 05 — /skills + /skill semantics', () => {
  it('/skills exists with kind:route and routeTemplate yielding /{ws}/skills', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills');
    expect(cmd).toBeDefined();
    expect(cmd!.kind).toBe('route');
    expect(cmd!.keyword).toBe('/skills');
    expect(cmd!.routeTemplate?.('alpha')).toBe('/alpha/skills');
  });

  it('/skill description is "Open a skill by name" (was "Run a skill")', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skill');
    expect(cmd).toBeDefined();
    expect(cmd!.description).toBe('Open a skill by name');
  });

  it('/skill no longer carries stubTolerant flag (the route is no longer a stub)', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skill');
    expect(cmd).toBeDefined();
    expect(cmd!.stubTolerant).toBeUndefined();
  });

  it('typing "sk" in filterCommands surfaces /skills before /skill', () => {
    const matches = filterCommands('sk');
    const ids = matches.map((c) => c.id);
    expect(ids).toContain('skills');
    expect(ids).toContain('skill');
    expect(ids.indexOf('skills')).toBeLessThan(ids.indexOf('skill'));
  });
});

describe('Phase 92 Plan 03 — /skills-graph entry', () => {
  // Multi-token `/skills graph` is impossible (shouldTrigger rejects
  // whitespace at slash-extension.ts:213). UI-SPEC OQ4 explicitly accepts
  // the single-token `/skills-graph` as the locked fallback. This suite
  // pins the contract so future refactors can't silently break it.

  it('SLASH_COMMANDS contains exactly one entry with id === "skills-graph"', () => {
    const matches = SLASH_COMMANDS.filter((c) => c.id === 'skills-graph');
    expect(matches).toHaveLength(1);
  });

  it('/skills-graph has keyword === "/skills-graph"', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills-graph');
    expect(cmd).toBeDefined();
    expect(cmd!.keyword).toBe('/skills-graph');
  });

  it('/skills-graph kind === "route"', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills-graph');
    expect(cmd!.kind).toBe('route');
  });

  it('/skills-graph routeTemplate yields /{ws}/skills?view=graph', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills-graph');
    expect(cmd!.routeTemplate?.('foo')).toBe('/foo/skills?view=graph');
  });

  it('/skills-graph carries SKILL violet iconColor (#7c5cff)', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills-graph');
    expect(cmd!.iconColor).toBe('#7c5cff');
  });

  it('/skills-graph uses the Network icon (matches /kg graph-shape semantics)', () => {
    const cmd = SLASH_COMMANDS.find((c) => c.id === 'skills-graph');
    expect(cmd!.iconName).toBe('Network');
  });

  it('filterCommands("graph") surfaces the /skills-graph entry', () => {
    const matches = filterCommands('graph');
    expect(matches.some((c) => c.id === 'skills-graph')).toBe(true);
  });

  it('typing "sk" surfaces /skills, /skills-graph, /skill in that order', () => {
    const matches = filterCommands('sk');
    const ids = matches.map((c) => c.id);
    expect(ids).toContain('skills');
    expect(ids).toContain('skills-graph');
    expect(ids).toContain('skill');
    expect(ids.indexOf('skills')).toBeLessThan(ids.indexOf('skills-graph'));
    expect(ids.indexOf('skills-graph')).toBeLessThan(ids.indexOf('skill'));
  });

  it('shouldTrigger accepts single-token "/skills-graph" (no whitespace)', () => {
    expect(shouldTrigger({ textBeforeCursor: '/skills-graph' })).toBe(true);
  });

  it('shouldTrigger rejects multi-token "/skills graph" (whitespace fallback proof)', () => {
    expect(shouldTrigger({ textBeforeCursor: '/skills graph' })).toBe(false);
  });

  it('existing /skills + /skill entries remain unchanged', () => {
    const skills = SLASH_COMMANDS.find((c) => c.id === 'skills');
    expect(skills!.routeTemplate?.('alpha')).toBe('/alpha/skills');
    const skill = SLASH_COMMANDS.find((c) => c.id === 'skill');
    expect(skill!.kind).toBe('picker');
  });
});
