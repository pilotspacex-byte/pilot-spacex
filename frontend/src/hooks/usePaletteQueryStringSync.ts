'use client';

/**
 * usePaletteQueryStringSync — two-way bind UIStore command-palette state to URL.
 *
 * Mount-only effect reads `?palette=1` and `?scope=<value>` from URL and seeds
 * the UIStore. After mount a MobX `reaction` writes URL params when
 * commandPaletteOpen / paletteScope change. Initial query text (`?q=`) is NOT
 * mirrored into the store — that input belongs to CommandPalette local state.
 *
 * Threat model T-90-01 (Tampering, `?scope=`): scope is whitelisted against
 * the PaletteScope union before being applied to the store; invalid values
 * are silently ignored (scope stays 'all').
 *
 * Source-of-truth pattern matches use-artifact-peek-state.ts (Phase 86).
 */

import { useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { reaction } from 'mobx';
import { useUIStore } from '@/stores';
import type { PaletteScope } from '@/stores/UIStore';

const VALID_SCOPES: readonly PaletteScope[] = [
  'all',
  'chats',
  'topics',
  'tasks',
  'specs',
  'skills',
  'people',
] as const;

function isValidScope(value: string | null): value is PaletteScope {
  return value !== null && (VALID_SCOPES as readonly string[]).includes(value);
}

export function usePaletteQueryStringSync(): void {
  const uiStore = useUIStore();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Mount-only: hydrate UIStore from URL.
  useEffect(() => {
    if (searchParams.get('palette') === '1') {
      uiStore.openCommandPalette();
    }
    const rawScope = searchParams.get('scope');
    if (isValidScope(rawScope)) {
      uiStore.setPaletteScope(rawScope);
    }
    // intentionally mount-only — re-running on every searchParams flip
    // would fight the reaction below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Post-mount: write URL when store changes.
  useEffect(() => {
    const dispose = reaction(
      () => ({ open: uiStore.commandPaletteOpen, scope: uiStore.paletteScope }),
      ({ open, scope }) => {
        if (typeof window === 'undefined') return;
        const params = new URLSearchParams(window.location.search);
        if (open) {
          params.set('palette', '1');
          if (scope !== 'all') params.set('scope', scope);
          else params.delete('scope');
        } else {
          params.delete('palette');
          params.delete('scope');
          params.delete('q');
        }
        const qs = params.toString();
        router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      }
    );
    return () => dispose();
  }, [uiStore, router, pathname]);
}
