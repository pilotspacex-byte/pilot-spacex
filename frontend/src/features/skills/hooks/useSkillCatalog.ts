/**
 * useSkillCatalog — TanStack Query for the skills gallery (Plan 91-03).
 *
 * Decision (D-91-02-B): named `useSkillCatalog` (not `useSkills`) to avoid
 * collision with the pre-existing chat composer hook at
 * `frontend/src/features/ai/ChatView/hooks/useSkills.ts`. The two hooks read
 * the same endpoint but compose different result shapes — chat merges system
 * skills with user/session skills, gallery wants the raw `Skill[]` only.
 *
 * Cache key choice: `['skills', 'catalog']` is intentionally distinct from the
 * chat hook's `['skills']`. They will not invalidate each other on a typical
 * `invalidateQueries({ queryKey: ['skills', 'catalog'] })` call; an
 * "all skills" invalidation (`['skills']`) would still flush both because
 * TanStack treats query keys as prefix matches.
 */
'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { skillsApi } from '@/services/api/skills';
import { ApiError } from '@/services/api/client';
import type { Skill } from '@/types/skill';

export const SKILLS_CATALOG_QUERY_KEY = ['skills', 'catalog'] as const;

export function useSkillCatalog(): UseQueryResult<Skill[], ApiError> {
  return useQuery<Skill[], ApiError>({
    queryKey: SKILLS_CATALOG_QUERY_KEY,
    queryFn: () => skillsApi.list(),
    // Skills are filesystem-backed and change rarely within a session; favor a
    // long staleTime to avoid pointless refetches on tab focus.
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: 1,
  });
}
