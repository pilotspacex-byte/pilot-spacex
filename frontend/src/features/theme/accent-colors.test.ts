import { describe, it, expect, beforeEach } from 'vitest';
import { ACCENT_PRESETS, applyAccentColor } from './accent-colors';
import type { AccentColor, ThemeMode } from './types';

describe('ACCENT_PRESETS', () => {
  it('has exactly 8 entries', () => {
    expect(Object.keys(ACCENT_PRESETS)).toHaveLength(8);
  });

  it('each preset has id, label, lightHex, darkHex', () => {
    const requiredKeys = [
      'id',
      'label',
      'lightHex',
      'darkHex',
      'hoverLight',
      'hoverDark',
      'mutedLight',
      'mutedDark',
    ];
    for (const [key, preset] of Object.entries(ACCENT_PRESETS)) {
      for (const rk of requiredKeys) {
        expect(preset).toHaveProperty(rk);
      }
      expect(preset.id).toBe(key);
      expect(preset.label).toBeTruthy();
      expect(preset.lightHex).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(preset.darkHex).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });

  it('contains the expected color keys', () => {
    const expected: AccentColor[] = [
      'green',
      'blue',
      'purple',
      'orange',
      'pink',
      'red',
      'teal',
      'indigo',
    ];
    expect(Object.keys(ACCENT_PRESETS).sort()).toEqual(expected.sort());
  });
});

describe('applyAccentColor', () => {
  beforeEach(() => {
    // Reset all custom properties
    const style = document.documentElement.style;
    style.removeProperty('--primary');
    style.removeProperty('--primary-hover');
    style.removeProperty('--primary-muted');
    style.removeProperty('--ring');
    style.removeProperty('--sidebar-primary');
    style.removeProperty('--sidebar-ring');
    style.removeProperty('--primary-text');
    style.removeProperty('--success');
    style.removeProperty('--editorCursor');
  });

  it('sets --primary to green lightHex in light mode', () => {
    applyAccentColor('green', 'light');
    expect(document.documentElement.style.getPropertyValue('--primary')).toBe(
      ACCENT_PRESETS.green.lightHex
    );
  });

  it('sets --primary to blue darkHex in dark mode', () => {
    applyAccentColor('blue', 'dark');
    expect(document.documentElement.style.getPropertyValue('--primary')).toBe(
      ACCENT_PRESETS.blue.darkHex
    );
  });

  it('updates all expected CSS variables', () => {
    applyAccentColor('purple', 'light');
    const style = document.documentElement.style;

    expect(style.getPropertyValue('--primary')).toBe(ACCENT_PRESETS.purple.lightHex);
    expect(style.getPropertyValue('--primary-hover')).toBe(ACCENT_PRESETS.purple.hoverLight);
    expect(style.getPropertyValue('--primary-muted')).toBe(ACCENT_PRESETS.purple.mutedLight);
    expect(style.getPropertyValue('--ring')).toBe(ACCENT_PRESETS.purple.lightHex);
    expect(style.getPropertyValue('--sidebar-primary')).toBe(ACCENT_PRESETS.purple.lightHex);
    expect(style.getPropertyValue('--sidebar-ring')).toBe(ACCENT_PRESETS.purple.lightHex);
    expect(style.getPropertyValue('--success')).toBe(ACCENT_PRESETS.purple.lightHex);
  });

  it('uses dark values when mode is dark', () => {
    applyAccentColor('orange', 'dark');
    const style = document.documentElement.style;

    expect(style.getPropertyValue('--primary')).toBe(ACCENT_PRESETS.orange.darkHex);
    expect(style.getPropertyValue('--primary-hover')).toBe(ACCENT_PRESETS.orange.hoverDark);
    expect(style.getPropertyValue('--primary-muted')).toBe(ACCENT_PRESETS.orange.mutedDark);
    expect(style.getPropertyValue('--ring')).toBe(ACCENT_PRESETS.orange.darkHex);
    expect(style.getPropertyValue('--sidebar-primary')).toBe(ACCENT_PRESETS.orange.darkHex);
  });
});

describe('ThemeMode type', () => {
  it('accepts all valid theme modes', () => {
    // Type-level test: these assignments should compile without error
    const modes: ThemeMode[] = ['light', 'dark', 'high-contrast', 'system'];
    expect(modes).toHaveLength(4);
  });
});
