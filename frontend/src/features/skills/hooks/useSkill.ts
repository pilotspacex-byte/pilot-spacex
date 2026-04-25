/**
 * useSkill — TanStack Query for a single skill detail (Plan 91-04).
 *
 * 404s must surface immediately to the detail page (so it can render the
 * "Skill not found" empty state) — hence the explicit no-retry branch on
 * `error.status === 404`. Other errors retry once.
 */
'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { skillsApi } from '@/services/api/skills';
import { ApiError } from '@/services/api/client';
import type { SkillDetail } from '@/types/skill';

/**
 * Build a stable query key for a skill detail. Returns a sentinel when slug is
 * undefined so two simultaneous undefined-slug renders don't accidentally
 * collide with a real cache entry.
 */
export function skillQueryKey(slug: string | undefined) {
  return ['skills', slug ?? '__undefined__'] as const;
}

export function useSkill(slug: string | undefined): UseQueryResult<SkillDetail, ApiError> {
  return useQuery<SkillDetail, ApiError>({
    queryKey: skillQueryKey(slug),
    queryFn: () => skillsApi.get(slug as string),
    enabled: Boolean(slug),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: (failureCount, error) => {
      // 404 is a deterministic answer — no retry. Other failures retry once.
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });
}
