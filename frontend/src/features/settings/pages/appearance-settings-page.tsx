'use client';

import { observer } from 'mobx-react-lite';
import { Monitor, Moon, Sun, SunMoon, Contrast } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useThemeStore } from '@/stores/RootStore';
import { ACCENT_PRESETS } from '@/features/theme';
import type { ThemeMode, AccentColor } from '@/features/theme';

const THEME_MODES: { id: ThemeMode; label: string; icon: React.ElementType; description: string }[] = [
  { id: 'light', label: 'Light', icon: Sun, description: 'Light background with dark text' },
  { id: 'dark', label: 'Dark', icon: Moon, description: 'Dark background with light text' },
  { id: 'high-contrast', label: 'High Contrast', icon: Contrast, description: 'Maximum contrast for accessibility' },
  { id: 'system', label: 'System', icon: Monitor, description: 'Follow your OS preference' },
];

/**
 * Appearance settings page -- theme mode, accent colors, editor theme.
 * Uses ThemeStore observables directly (observer component).
 */
export const AppearanceSettingsPage = observer(function AppearanceSettingsPage() {
  const themeStore = useThemeStore();

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Appearance</h2>
        <p className="text-sm text-muted-foreground">
          Customize the look and feel of Pilot Space.
        </p>
      </div>

      {/* Theme Mode */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-foreground">Theme</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {THEME_MODES.map((mode) => {
            const isActive = themeStore.themeMode === mode.id;
            const Icon = mode.icon;
            return (
              <button
                key={mode.id}
                onClick={() => themeStore.setThemeMode(mode.id)}
                className={cn(
                  'flex flex-col items-center gap-2 rounded-xl border p-4 transition-all duration-200',
                  'hover:border-primary/50 hover:shadow-warm-sm',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isActive
                    ? 'border-primary bg-primary/5 shadow-warm-sm'
                    : 'border-border bg-card'
                )}
                aria-pressed={isActive}
              >
                <Icon className={cn('h-5 w-5', isActive ? 'text-primary' : 'text-muted-foreground')} />
                <span className={cn('text-xs font-medium', isActive ? 'text-foreground' : 'text-muted-foreground')}>
                  {mode.label}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Accent Color */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-foreground">Accent Color</h3>
        <p className="text-xs text-muted-foreground">
          Choose a color for buttons, links, and active indicators.
        </p>
        <div className="flex flex-wrap gap-3">
          {Object.values(ACCENT_PRESETS).map((preset) => {
            const isActive = themeStore.accentColor === preset.id;
            const hex =
              themeStore.resolvedMode === 'dark' || themeStore.resolvedMode === 'high-contrast'
                ? preset.darkHex
                : preset.lightHex;
            return (
              <button
                key={preset.id}
                onClick={() => themeStore.setAccentColor(preset.id as AccentColor)}
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-200',
                  'hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  isActive ? 'border-foreground scale-110' : 'border-transparent'
                )}
                style={{ backgroundColor: hex }}
                aria-label={preset.label}
                aria-pressed={isActive}
                title={preset.label}
              >
                {isActive && (
                  <SunMoon className="h-4 w-4 text-white drop-shadow-sm" />
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* Editor Theme placeholder -- full .tmTheme import from Plan 03 */}
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-foreground">Editor Theme</h3>
        <p className="text-xs text-muted-foreground">
          The code editor automatically matches your theme mode. Custom theme import coming soon.
        </p>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">
            Current editor theme:{' '}
            <span className="font-medium text-foreground">{themeStore.effectiveMonacoTheme}</span>
          </p>
        </div>
      </section>
    </div>
  );
});
