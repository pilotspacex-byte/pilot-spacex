'use client';

/**
 * useMediaQuery - Hook for responsive breakpoint detection
 *
 * Provides SSR-safe media query matching with automatic updates on resize.
 * Uses useSyncExternalStore for proper React 18+ synchronization.
 *
 * @example
 * ```tsx
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const isDesktop = useMediaQuery('(min-width: 1024px)');
 * ```
 */
import { useSyncExternalStore, useCallback } from 'react';

/**
 * Tailwind CSS breakpoints
 */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Hook to detect if a media query matches
 * Uses useSyncExternalStore for proper React 18+ external state synchronization
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (callback: () => void) => {
      if (typeof window === 'undefined') {
        return () => {};
      }
      const mediaQuery = window.matchMedia(query);
      mediaQuery.addEventListener('change', callback);
      return () => {
        mediaQuery.removeEventListener('change', callback);
      };
    },
    [query]
  );

  const getSnapshot = useCallback(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.matchMedia(query).matches;
  }, [query]);

  const getServerSnapshot = useCallback(() => {
    // Default to false on server
    return false;
  }, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Hook to detect if viewport is at or above a breakpoint
 *
 * @example
 * ```tsx
 * const isDesktop = useBreakpoint('lg'); // true if >= 1024px
 * ```
 */
export function useBreakpoint(breakpoint: Breakpoint): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS[breakpoint]}px)`);
}

/**
 * Hook to detect if viewport is below a breakpoint
 *
 * @example
 * ```tsx
 * const isMobile = useBreakpointDown('md'); // true if < 768px
 * ```
 */
export function useBreakpointDown(breakpoint: Breakpoint): boolean {
  return useMediaQuery(`(max-width: ${BREAKPOINTS[breakpoint] - 1}px)`);
}

/**
 * Hook to detect if viewport is between two breakpoints
 *
 * @example
 * ```tsx
 * const isTablet = useBreakpointBetween('md', 'lg'); // true if 768px - 1023px
 * ```
 */
export function useBreakpointBetween(min: Breakpoint, max: Breakpoint): boolean {
  return useMediaQuery(
    `(min-width: ${BREAKPOINTS[min]}px) and (max-width: ${BREAKPOINTS[max] - 1}px)`
  );
}

/**
 * Hook to get current breakpoint range
 *
 * @example
 * ```tsx
 * const { isMobile, isTablet, isDesktop } = useResponsive();
 * ```
 */
export function useResponsive() {
  const isMobile = useBreakpointDown('md');
  const isTablet = useBreakpointBetween('md', 'lg');
  const isDesktop = useBreakpoint('lg');
  const isLargeDesktop = useBreakpoint('xl');

  return {
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    // Convenience aliases
    isSmallScreen: isMobile || isTablet,
    isLargeScreen: isDesktop,
  };
}

/**
 * Hook to detect reduced motion preference
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

/**
 * Hook to detect dark mode preference
 */
export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

/**
 * Hook to get window dimensions with SSR safety
 * Uses useSyncExternalStore for proper React 18+ synchronization
 */
export function useWindowSize() {
  const subscribe = useCallback((callback: () => void) => {
    if (typeof window === 'undefined') {
      return () => {};
    }
    window.addEventListener('resize', callback);
    return () => window.removeEventListener('resize', callback);
  }, []);

  const getSnapshot = useCallback(() => {
    if (typeof window === 'undefined') {
      return { width: 0, height: 0 };
    }
    return {
      width: window.innerWidth,
      height: window.innerHeight,
    };
  }, []);

  const getServerSnapshot = useCallback(() => {
    return { width: 0, height: 0 };
  }, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
