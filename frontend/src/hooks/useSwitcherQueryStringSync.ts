'use client';

/**
 * useSwitcherQueryStringSync — two-way bind UIStore.workspaceSwitcherOpen to URL.
 *
 * Mount-only effect reads `?switcher=1` and seeds the UIStore. After mount a
 * MobX `reaction` writes / strips the `switcher` param when the observable
 * flips.
 *
 * Mirrors usePaletteQueryStringSync but with no scope dimension.
 */

import { useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { reaction } from 'mobx';
import { useUIStore } from '@/stores';

export function useSwitcherQueryStringSync(): void {
  const uiStore = useUIStore();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Mount-only: hydrate from URL.
  useEffect(() => {
    if (searchParams.get('switcher') === '1') {
      uiStore.openWorkspaceSwitcher();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Post-mount: write URL when store changes.
  useEffect(() => {
    const dispose = reaction(
      () => uiStore.workspaceSwitcherOpen,
      (open) => {
        if (typeof window === 'undefined') return;
        const params = new URLSearchParams(window.location.search);
        if (open) {
          params.set('switcher', '1');
        } else {
          params.delete('switcher');
        }
        const qs = params.toString();
        router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      }
    );
    return () => dispose();
  }, [uiStore, router, pathname]);
}
