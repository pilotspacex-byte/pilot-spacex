'use client';

/**
 * useLenisScroll - Lenis smooth scrolling provider and hook.
 *
 * Provides spring-physics-based smooth scrolling for sidebar panels (file tree,
 * note list). Monaco editor viewports are excluded via `data-lenis-prevent`
 * attribute on their container elements.
 *
 * Respects `prefers-reduced-motion`: when enabled, sets `lerp: 1` for
 * instant scrolling (no interpolation).
 */

import type { ReactNode } from 'react';
import { useSyncExternalStore } from 'react';
import { ReactLenis, useLenis } from 'lenis/react';

/** Cached MediaQueryList to avoid re-parsing on every render/subscribe call */
let cachedMq: MediaQueryList | null = null;
function getMotionMq(): MediaQueryList {
  if (!cachedMq) cachedMq = window.matchMedia('(prefers-reduced-motion: reduce)');
  return cachedMq;
}

function subscribeReducedMotion(callback: () => void): () => void {
  const mq = getMotionMq();
  mq.addEventListener('change', callback);
  return () => mq.removeEventListener('change', callback);
}

function getReducedMotionSnapshot(): boolean {
  return getMotionMq().matches;
}

function getReducedMotionServerSnapshot(): boolean {
  return false;
}

/**
 * SmoothScrollProvider wraps children with Lenis smooth scrolling.
 *
 * Should be placed around the main workspace content area, NOT around
 * modals or settings panels. Monaco editors self-exclude via
 * `data-lenis-prevent`.
 */
export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  const reducedMotion = useSyncExternalStore(
    subscribeReducedMotion,
    getReducedMotionSnapshot,
    getReducedMotionServerSnapshot
  );

  return (
    <ReactLenis
      root
      options={{
        lerp: reducedMotion ? 1 : 0.1,
        duration: 1.2,
        smoothWheel: true,
        touchMultiplier: 2,
      }}
    >
      {children}
    </ReactLenis>
  );
}

/**
 * useLenisScroll returns the current Lenis instance for programmatic
 * scroll control (e.g., scrollTo, stop, start).
 */
export function useLenisScroll() {
  const lenis = useLenis();
  return lenis;
}
