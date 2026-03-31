'use client';

import { useCallback, useSyncExternalStore } from 'react';
import { PILOT_SPACE_LIGHT, PILOT_SPACE_DARK } from '../themes/pilotSpaceTheme';

function getSnapshot(): string {
  return document.documentElement.classList.contains('dark')
    ? PILOT_SPACE_DARK
    : PILOT_SPACE_LIGHT;
}

function getServerSnapshot(): string {
  return PILOT_SPACE_LIGHT;
}

/**
 * useMonacoTheme — React hook that returns the current Monaco theme name.
 *
 * Uses useSyncExternalStore to subscribe to class changes on <html> via
 * MutationObserver, avoiding the setState-in-effect pattern that triggers
 * cascading renders.
 */
export function useMonacoTheme(): { theme: string } {
  const subscribe = useCallback((onStoreChange: () => void) => {
    const observer = new MutationObserver(onStoreChange);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
    return () => observer.disconnect();
  }, []);

  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return { theme };
}
