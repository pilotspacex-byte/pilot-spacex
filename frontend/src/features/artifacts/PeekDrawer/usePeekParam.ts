'use client';

/**
 * usePeekParam — URL-driven state hook for the PeekDrawer.
 *
 * URL contract: `?peek=<type>:<id>`
 *   - type: lowercase artifact type (`note`, `issue`, `spec`, `decision`,
 *     `md`, `html`, `code`, `pdf`, `csv`, `img`, `pptx`, `link`)
 *   - id:   UUID or slug, depending on type
 *
 * The hook parses the param on the first render (deep-link support), updates
 * via `router.replace` so browser history isn't polluted, and memoises the
 * imperative open/close helpers so they are safe to pass into `useCallback`
 * dependencies downstream.
 */

import { useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type { ArtifactType } from '../ArtifactCard';

const PEEK_PARAM = 'peek';

const VALID_PEEK_TYPES: ReadonlySet<string> = new Set([
  'note',
  'issue',
  'spec',
  'decision',
  'md',
  'html',
  'code',
  'pdf',
  'csv',
  'img',
  'pptx',
  'link',
]);

export interface PeekTarget {
  type: ArtifactType;
  id: string;
}

export interface PeekParamAPI {
  isOpen: boolean;
  peekType: ArtifactType | null;
  peekId: string | null;
  openPeek: (target: PeekTarget) => void;
  closePeek: () => void;
}

function parsePeekValue(raw: string | null): PeekTarget | null {
  if (!raw) return null;
  const colon = raw.indexOf(':');
  if (colon < 1 || colon === raw.length - 1) return null;
  const type = raw.slice(0, colon).toLowerCase();
  const id = raw.slice(colon + 1);
  if (!VALID_PEEK_TYPES.has(type)) return null;
  if (!id) return null;
  return { type: type.toUpperCase() as ArtifactType, id };
}

export function usePeekParam(): PeekParamAPI {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Derived state — computed from the URL on every render. Cheap: the
  // URLSearchParams.get call is O(1) amortised.
  const peekTarget = useMemo(
    () => parsePeekValue(searchParams?.get(PEEK_PARAM) ?? null),
    [searchParams]
  );

  const writeParam = useCallback(
    (next: PeekTarget | null) => {
      const params = new URLSearchParams(searchParams?.toString() ?? '');
      if (next) {
        params.set(PEEK_PARAM, `${next.type.toLowerCase()}:${next.id}`);
      } else {
        params.delete(PEEK_PARAM);
      }
      const query = params.toString();
      // Use replace() so opening/closing the drawer doesn't pollute history.
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const openPeek = useCallback((target: PeekTarget) => writeParam(target), [writeParam]);
  const closePeek = useCallback(() => writeParam(null), [writeParam]);

  return {
    isOpen: peekTarget !== null,
    peekType: peekTarget?.type ?? null,
    peekId: peekTarget?.id ?? null,
    openPeek,
    closePeek,
  };
}
