/**
 * Accent color presets and CSS injection utility for Pilot Space theme engine.
 *
 * 8 accent colors, each with light/dark hex, hover, and muted variants.
 * applyAccentColor() updates CSS custom properties on document.documentElement.
 */

import type { AccentColor, AccentPreset } from './types';

/**
 * 8 accent color presets with light/dark mode variants.
 *
 * green is the default (matches existing --primary: #29a386 / #3db896).
 * Hover values are ~10% darker. Muted values are ~90% lighter (light) / 15% opacity (dark).
 */
export const ACCENT_PRESETS: Record<AccentColor, AccentPreset> = {
  green: {
    id: 'green',
    label: 'Green',
    lightHex: '#29a386',
    darkHex: '#3db896',
    hoverLight: '#238f75',
    hoverDark: '#35a384',
    mutedLight: '#e8f5f1',
    mutedDark: '#1f3d35',
  },
  blue: {
    id: 'blue',
    label: 'Blue',
    lightHex: '#3b82f6',
    darkHex: '#60a5fa',
    hoverLight: '#2563eb',
    hoverDark: '#4e94e8',
    mutedLight: '#eff6ff',
    mutedDark: '#1e2d45',
  },
  purple: {
    id: 'purple',
    label: 'Purple',
    lightHex: '#8b5cf6',
    darkHex: '#a78bfa',
    hoverLight: '#7c3aed',
    hoverDark: '#9679e8',
    mutedLight: '#f5f3ff',
    mutedDark: '#2d2345',
  },
  orange: {
    id: 'orange',
    label: 'Orange',
    lightHex: '#f97316',
    darkHex: '#fb923c',
    hoverLight: '#ea580c',
    hoverDark: '#e8822e',
    mutedLight: '#fff7ed',
    mutedDark: '#3d2a1a',
  },
  pink: {
    id: 'pink',
    label: 'Pink',
    lightHex: '#ec4899',
    darkHex: '#f472b6',
    hoverLight: '#db2777',
    hoverDark: '#e260a4',
    mutedLight: '#fdf2f8',
    mutedDark: '#3d1f30',
  },
  red: {
    id: 'red',
    label: 'Red',
    lightHex: '#ef4444',
    darkHex: '#f87171',
    hoverLight: '#dc2626',
    hoverDark: '#e65f5f',
    mutedLight: '#fef2f2',
    mutedDark: '#3d1f1f',
  },
  teal: {
    id: 'teal',
    label: 'Teal',
    lightHex: '#14b8a6',
    darkHex: '#2dd4bf',
    hoverLight: '#0d9488',
    hoverDark: '#26bfac',
    mutedLight: '#f0fdfa',
    mutedDark: '#1a3d38',
  },
  indigo: {
    id: 'indigo',
    label: 'Indigo',
    lightHex: '#6366f1',
    darkHex: '#818cf8',
    hoverLight: '#4f46e5',
    hoverDark: '#717ae6',
    mutedLight: '#eef2ff',
    mutedDark: '#232545',
  },
};

/**
 * Apply accent color CSS custom properties to document.documentElement.
 *
 * Sets --primary, --primary-hover, --primary-muted, --ring, --sidebar-primary,
 * --sidebar-ring, --primary-text, and --success variables.
 *
 * @param color - The accent color preset to apply
 * @param mode - 'light' or 'dark' determines which hex values to use
 */
export function applyAccentColor(color: AccentColor, mode: 'light' | 'dark'): void {
  const preset = ACCENT_PRESETS[color];
  if (!preset) return;

  const isLight = mode === 'light';
  const primary = isLight ? preset.lightHex : preset.darkHex;
  const hover = isLight ? preset.hoverLight : preset.hoverDark;
  const muted = isLight ? preset.mutedLight : preset.mutedDark;
  // AA-compliant text: darker variant in light, lighter variant in dark
  const primaryText = isLight ? preset.hoverLight : preset.darkHex;

  const el = document.documentElement.style;
  el.setProperty('--primary', primary);
  el.setProperty('--primary-hover', hover);
  el.setProperty('--primary-muted', muted);
  el.setProperty('--ring', primary);
  el.setProperty('--sidebar-primary', primary);
  el.setProperty('--sidebar-ring', primary);
  el.setProperty('--primary-text', primaryText);
  el.setProperty('--success', primary);
}
