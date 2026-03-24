/**
 * Theme system types for Pilot Space multi-theme engine.
 */

/** Supported theme modes */
export type ThemeMode = 'light' | 'dark' | 'high-contrast' | 'system';

/** Available accent color presets */
export type AccentColor =
  | 'green'
  | 'blue'
  | 'purple'
  | 'orange'
  | 'pink'
  | 'red'
  | 'teal'
  | 'indigo';

/** Full theme preferences persisted per-user */
export interface ThemePreferences {
  themeMode: ThemeMode;
  accentColor: AccentColor;
  editorThemeId: string | null;
  fontSize: number;
  fontFamily: string;
}

/** Accent color preset definition */
export interface AccentPreset {
  id: AccentColor;
  label: string;
  lightHex: string;
  darkHex: string;
  hoverLight: string;
  hoverDark: string;
  mutedLight: string;
  mutedDark: string;
}

/** Default theme preferences */
export const DEFAULT_PREFERENCES: ThemePreferences = {
  themeMode: 'system',
  accentColor: 'green',
  editorThemeId: null,
  fontSize: 14,
  fontFamily: 'default',
};
