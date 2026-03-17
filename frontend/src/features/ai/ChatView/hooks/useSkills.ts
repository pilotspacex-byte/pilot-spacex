/**
 * Hook for fetching available skills from the backend.
 * Merges system skills (from templates) with user's personal skills.
 */

import { useQuery } from '@tanstack/react-query';
import { aiApi } from '@/services/api/ai';
import { userSkillsApi, type UserSkill } from '@/services/api/user-skills';
import type { SkillDefinition } from '../types';
import { FALLBACK_SKILLS, SESSION_SKILLS } from '../constants';

/**
 * Convert a UserSkill to a SkillDefinition for the chat menu.
 */
function userSkillToDefinition(skill: UserSkill): SkillDefinition {
  const displayName = skill.skill_name || skill.template_name || 'Custom Skill';
  // Extract first meaningful line from skill_content as description
  const lines = skill.skill_content.split('\n').filter((l) => l.trim() && !l.startsWith('#'));
  const description = lines[0]?.trim().slice(0, 100) || displayName;

  // Use kebab-case display name for the menu label (e.g., "senior-tdd-developer")
  const baseSlug = displayName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  const slug = baseSlug ? `${baseSlug}-${skill.id.slice(0, 8)}` : `skill-${skill.id.slice(0, 8)}`;

  return {
    name: slug,
    description,
    category: 'my-skills',
    icon: 'UserCog',
    examples: [],
  };
}

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
  userSkills: UserSkill[] | undefined,
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

  const personalSkills: SkillDefinition[] = (userSkills ?? [])
    .filter((s) => s.is_active)
    .map(userSkillToDefinition);

  return [...SESSION_SKILLS, ...personalSkills, ...backendSkills];
}

export function useSkills(workspaceId?: string) {
  const systemQuery = useQuery({
    queryKey: ['skills'],
    queryFn: async () => {
      const res = await aiApi.listSkills();
      return res.skills;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
    retry: 1,
  });

  const userQuery = useQuery({
    queryKey: ['user-skills', workspaceId],
    queryFn: () => userSkillsApi.getUserSkills(workspaceId!),
    staleTime: 60_000,
    enabled: !!workspaceId,
    retry: 1,
  });

  const skills = mergeSkills(systemQuery.data, userQuery.data, FALLBACK_SKILLS);

  return {
    skills,
    isLoading: systemQuery.isLoading || userQuery.isLoading,
    error: systemQuery.error || userQuery.error,
  };
}
