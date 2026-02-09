/**
 * Hook for fetching available skills from the backend.
 * Uses TanStack Query with long stale time since skills rarely change.
 */

import { useQuery } from '@tanstack/react-query';
import { aiApi } from '@/services/api/ai';
import type { SkillDefinition } from '../types';
import { FALLBACK_SKILLS, SESSION_SKILLS } from '../constants';

/**
 * Merge API skills with session-only skills and provide fallback.
 */
function mergeSkills(
  apiSkills:
    | Array<{
        name: string;
        description: string;
        category: string;
        icon: string;
        examples: string[];
      }>
    | undefined,
  fallback: SkillDefinition[]
): SkillDefinition[] {
  const backendSkills: SkillDefinition[] = apiSkills
    ? apiSkills.map((s) => ({
        name: s.name,
        description: s.description,
        category: s.category as SkillDefinition['category'],
        icon: s.icon,
        examples: s.examples,
      }))
    : fallback;

  return [...SESSION_SKILLS, ...backendSkills];
}

export function useSkills() {
  const query = useQuery({
    queryKey: ['skills'],
    queryFn: async () => {
      const res = await aiApi.listSkills();
      return res.skills;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    retry: 1,
  });

  const skills = mergeSkills(query.data, FALLBACK_SKILLS);

  return {
    skills,
    isLoading: query.isLoading,
    error: query.error,
  };
}
